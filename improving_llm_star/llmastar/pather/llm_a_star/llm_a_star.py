import json
import math
import heapq
from time import perf_counter

from llmastar.env.search import env, plotting
from llmastar.model import ChatGPT, Llama3
from llmastar.utils import is_lines_collision, list_parse
from .prompt import *

class LLMAStar:
    """LLM-A* algorithm with cost + heuristics as the priority."""
    
    GPT_METHOD = "PARSE"
    GPT_LLMASTAR_METHOD = "LLM-A*"

    def __init__(self, llm='gpt', prompt='standard', alpha=1.0, track_progress=False,
                 adaptive_alpha=False, stagnation_threshold=30, alpha_decrease=0.2,
                 alpha_increase=0.1, alpha_min=0.2, alpha_max=1.0,
                 alpha_update_interval=10, progress_epsilon=1e-9):
        for name, value in [("stagnation_threshold", stagnation_threshold),
                            ("alpha_update_interval", alpha_update_interval)]:
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if not all(math.isfinite(v) for v in
                   (alpha_min, alpha_max, alpha_decrease, alpha_increase, progress_epsilon)):
            raise ValueError("Adaptive parameters must be finite")
        if not 0 <= alpha_min <= alpha_max <= 1:
            raise ValueError("Require 0 <= alpha_min <= alpha_max <= 1")
        if alpha_decrease <= 0 or alpha_increase <= 0 or progress_epsilon < 0:
            raise ValueError("Alpha steps must be positive; progress_epsilon must be nonnegative")
        self.alpha = alpha
        self.track_progress = track_progress
        self.adaptive_alpha = adaptive_alpha
        self.stagnation_threshold = stagnation_threshold
        self.alpha_decrease = alpha_decrease
        self.alpha_increase = alpha_increase
        self.alpha_min, self.alpha_max = alpha_min, alpha_max
        self.alpha_update_interval = alpha_update_interval
        self.progress_epsilon = progress_epsilon
        self._progress_enabled = track_progress or adaptive_alpha
        self.waypoint_progress = []
        self.alpha_history = []
        self.alpha_adjustments = 0
        self.open_queue_rebuilds = 0
        self.search_metrics = {}
        self.llm = llm
        if self.llm == 'gpt':
            self.parser = ChatGPT(method=self.GPT_METHOD, sysprompt=sysprompt_parse, example=example_parse)
            self.model = ChatGPT(method=self.GPT_LLMASTAR_METHOD, sysprompt="", example=None)
        elif self.llm == 'llama':
            self.model = Llama3()
        else:
            raise ValueError("Invalid LLM model. Choose 'gpt' or 'llama'.")
        
        assert prompt in ['standard', 'cot', 'repe'], "Invalid prompt type. Choose 'standard', 'cot', or 'repe'."
        self.prompt = prompt

    def _parse_query(self, query):
        """Parse input query using the specified LLM model."""
        if isinstance(query, str):
            if self.llm == 'gpt':
                response = self.parser.chat(query)
                print(response)
                return json.loads(response)
            elif self.llm == 'llama':
                response = self.model.ask(parse_llama.format(query=query))
                print(response)
                return json.loads(response)
            else:
                raise ValueError("Invalid LLM model.")
        return query

    def _initialize_parameters(self, input_data):
        """Initialize environment parameters from input data."""
        self.s_start = tuple(input_data['start'])
        self.s_goal = tuple(input_data['goal'])
        self.horizontal_barriers = input_data['horizontal_barriers']
        self.vertical_barriers = input_data['vertical_barriers']
        self.range_x = input_data['range_x']
        self.range_y = input_data['range_y']
        self.Env = env.Env(self.range_x[1], self.range_y[1], self.horizontal_barriers, self.vertical_barriers)
        self.plot = plotting.Plotting(self.s_start, self.s_goal, self.Env)
        # Adjust range limits
        self.range_x[1] -= 1
        self.range_y[1] -= 1
        self.u_set = self.Env.motions
        self.obs = self.Env.obs
        self.OPEN = []
        self.CLOSED = []
        self.PARENT = dict()
        self.g = dict()

    def _initialize_llm_paths(self):
        """Initialize paths using LLM suggestions."""
        start, goal = list(self.s_start), list(self.s_goal)
        query = self._generate_llm_query(start, goal)

        if self.llm == 'gpt':
            response = self.model.ask(prompt=query, max_tokens=1000)
        elif self.llm == 'llama':
            response = self.model.ask(prompt=query)
        else:
            raise ValueError("Invalid LLM model.")

        nodes = list_parse(response)
        self.target_list = self._filter_valid_nodes(nodes)

        if not self.target_list or self.target_list[0] != self.s_start:
            self.target_list.insert(0, self.s_start)
        if not self.target_list or self.target_list[-1] != self.s_goal:
            self.target_list.append(self.s_goal)
        print(self.target_list)
        self.i = 1
        self.s_target = self.target_list[1]
        print(self.target_list[0], self.s_target)

    def _generate_llm_query(self, start, goal):
        """Generate the query for the LLM."""
        if self.llm == 'gpt':
            return gpt_prompt[self.prompt].format(start=start, goal=goal,
                                horizontal_barriers=self.horizontal_barriers,
                                vertical_barriers=self.vertical_barriers)
        elif self.llm == 'llama':
            return llama_prompt[self.prompt].format(start=start, goal=goal,
                                    horizontal_barriers=self.horizontal_barriers,
                                    vertical_barriers=self.vertical_barriers)

    def _filter_valid_nodes(self, nodes):
        """Filter out invalid nodes based on environment constraints."""
        return [(node[0], node[1]) for node in nodes
                if (node[0], node[1]) not in self.obs
                and self.range_x[0] + 1 < node[0] < self.range_x[1] - 1
                and self.range_y[0] + 1 < node[1] < self.range_y[1] - 1]

    def searching(self, query, filepath='temp.png'):
        """
        A* searching algorithm.
        :return: Path and search metrics.
        """
        self.filepath = filepath
        print(query)
        input_data = self._parse_query(query)
        self._initialize_parameters(input_data)
        self.waypoint_progress = []
        self.alpha_history = []
        self.alpha_adjustments = 0
        self.open_queue_rebuilds = 0
        self.search_metrics = {}
        self.path = []
        if self.adaptive_alpha:
            self.alpha = self.alpha_max
        self._initialize_llm_paths()
        if self._progress_enabled:
            self._start_waypoint_measurement()
        self._log_alpha_event("initial")
        search_started = perf_counter()
        
        self.PARENT[self.s_start] = self.s_start
        self.g[self.s_start] = 0
        heapq.heappush(self.OPEN, (self.f_value(self.s_start), self.s_start))

        goal_reached = False
        while self.OPEN:
            _, s = heapq.heappop(self.OPEN)
            self.CLOSED.append(s)
            if self._progress_enabled:
                self._record_waypoint_progress(s)

            if s == self.s_goal:  # stop condition
                goal_reached = True
                break

            for s_n in self.get_neighbor(s):
                if s_n == self.s_target and self.s_goal != self.s_target :
                    self._update_target()
                    self._update_queue()
                    print(s_n, self.s_target)
                    
                if s_n in self.CLOSED:
                    continue

                new_cost = self.g[s] + self.cost(s, s_n)
                if s_n not in self.g:
                    self.g[s_n] = math.inf
                    
                if new_cost < self.g[s_n]:  # conditions for updating Cost
                    self.g[s_n] = new_cost
                    self.PARENT[s_n] = s
                    heapq.heappush(self.OPEN, (self.f_value(s_n), s_n))

            if self.adaptive_alpha:
                self._maybe_update_alpha()

        path = self.extract_path(self.PARENT) if goal_reached else []
        self.path = path
        path_valid = self._is_valid_path(path)
        visited = self.CLOSED
        result = {
            "operation": len(self.CLOSED),
            "storage": len(self.g),
            "length": sum(self._euclidean_distance(path[i], path[i+1]) for i in range(len(path)-1)) if path_valid else math.inf,
            "llm_output": self.target_list
        }
        self.search_metrics = {
            "expanded_nodes": len(self.CLOSED),
            "unique_expanded_nodes": len(set(self.CLOSED)),
            "path_cost": result["length"] if path_valid else None,
            "path_valid": path_valid,
            "goal_reached": goal_reached,
            "alpha_adjustments": self.alpha_adjustments,
            "final_alpha": self.alpha,
            "open_queue_rebuilds": self.open_queue_rebuilds,
            "search_time_seconds": perf_counter() - search_started,
        }
        print(result)
        self.plot.animation(path, visited, True, "LLM-A*", self.filepath)
        return result

    @staticmethod
    def _euclidean_distance(p1, p2):
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    def _update_queue(self):
        if not self.OPEN:
            return
        queue = [(self.f_value(s), s) for _, s in self.OPEN]
        heapq.heapify(queue)
        self.OPEN = queue
        self.open_queue_rebuilds += 1

    def _update_target(self):
        """Update the current target in the path."""
        self.i += 1
        if self.i < len(self.target_list):
            self.s_target = self.target_list[self.i]
            if self._progress_enabled:
                self._start_waypoint_measurement()
            if self.adaptive_alpha:
                # The caller refreshes OPEN once for both target and alpha changes.
                if not self._set_alpha(self.alpha_max, "target_reset"):
                    self._log_alpha_event("target_reset")
                self.waypoint_progress[-1]["alpha"] = self.alpha

    def _start_waypoint_measurement(self):
        """Start a summary for one active target; never change search priorities."""
        self.waypoint_progress.append({
            "target_index": self.i,
            "target": self.s_target,
            "alpha": self.alpha,
            "expansions": 0,
            "initial_distance": None,
            "best_distance": None,
            "improvements": 0,
            "expansions_without_progress": 0,
            "max_expansions_without_progress": 0,
        })
        self._evaluated_improvements = 0

    def _record_waypoint_progress(self, s):
        """Measure Euclidean progress per heap pop, including baseline duplicates.

        The first pop after a target switch establishes the distance baseline.
        Strict improvements beyond numerical tolerance reset the stall counter.
        Summaries use O(number of target activations) storage, not a node trace.
        """
        summary = self.waypoint_progress[-1]
        summary["expansions"] += 1
        distance = math.hypot(self.s_target[0] - s[0], self.s_target[1] - s[1])

        if summary["initial_distance"] is None:
            summary["initial_distance"] = distance
            summary["best_distance"] = distance
        elif summary["best_distance"] - distance > self.progress_epsilon:
            summary["best_distance"] = distance
            summary["improvements"] += 1
            summary["expansions_without_progress"] = 0
        else:
            summary["expansions_without_progress"] += 1
            summary["max_expansions_without_progress"] = max(
                summary["max_expansions_without_progress"],
                summary["expansions_without_progress"],
            )

    def _maybe_update_alpha(self):
        summary = self.waypoint_progress[-1]
        if not summary["expansions"] or summary["expansions"] % self.alpha_update_interval:
            return
        improvements = summary["improvements"]
        if summary["expansions_without_progress"] >= self.stagnation_threshold:
            changed = self._set_alpha(self.alpha - self.alpha_decrease, "stagnation")
        elif improvements > self._evaluated_improvements:
            changed = self._set_alpha(self.alpha + self.alpha_increase, "progress")
        else:
            changed = False
        self._evaluated_improvements = improvements
        if changed:
            self._update_queue()

    def _set_alpha(self, value, reason):
        value = min(self.alpha_max, max(self.alpha_min, round(value, 12)))
        if math.isclose(value, self.alpha, rel_tol=0, abs_tol=1e-12):
            return False
        old_alpha = self.alpha
        self.alpha = value
        self.alpha_adjustments += 1
        self._log_alpha_event(reason, old_alpha)
        return True

    def _log_alpha_event(self, reason, old_alpha=None):
        summary = self.waypoint_progress[-1] if self.waypoint_progress else {}
        self.alpha_history.append({
            "expansion": len(self.CLOSED), "target_index": self.i,
            "target": self.s_target, "reason": reason,
            "old_alpha": old_alpha, "alpha": self.alpha,
            "best_distance": summary.get("best_distance"),
            "expansions_without_progress": summary.get("expansions_without_progress", 0),
            "improvements": summary.get("improvements", 0),
            "open_size": len(self.OPEN),
        })

    def _is_valid_path(self, path):
        if not path or path[0] != self.s_start or path[-1] != self.s_goal:
            return False
        if any(not (self.range_x[0] < x < self.range_x[1]
                    and self.range_y[0] < y < self.range_y[1]) for x, y in path):
            return False
        return all((b[0] - a[0], b[1] - a[1]) in self.u_set
                   and not self.is_collision(a, b) for a, b in zip(path, path[1:]))

    def get_neighbor(self, s):
        """Find neighbors of state s that are not in obstacles."""
        return [(s[0] + u[0], s[1] + u[1]) for u in self.u_set]

    def cost(self, s_start, s_goal):
        """Calculate cost for the motion from s_start to s_goal."""
        return math.inf if self.is_collision(s_start, s_goal) else math.hypot(s_goal[0] - s_start[0], s_goal[1] - s_start[1])

    def is_collision(self, s_start, s_end):
        """Check if the line segment (s_start, s_end) collides with any barriers."""
        line1 = [s_start, s_end]
        return any(is_lines_collision(line1, [[h[1], h[0]], [h[2], h[0]]]) for h in self.horizontal_barriers) or \
                any(is_lines_collision(line1, [[v[0], v[1]], [v[0], v[2]]]) for v in self.vertical_barriers) or \
                any(is_lines_collision(line1, [[x, self.range_y[0]], [x, self.range_y[1]]]) for x in self.range_x) or \
                any(is_lines_collision(line1, [[self.range_x[0], y], [self.range_x[1], y]]) for y in self.range_y)

    def f_value(self, s):
        """Compute the f-value for state s."""
        return self.g[s] + self.heuristic(s)

    def extract_path(self, PARENT):
        """Extract the path based on the PARENT set."""
        path = [self.s_goal]
        while path[-1] != self.s_start:
            path.append(PARENT[path[-1]])
        return path[::-1]

    def heuristic(self, s):
        """Combine goal distance with waypoint distance weighted by alpha."""
        goal_distance = math.hypot(
            self.s_goal[0] - s[0], self.s_goal[1] - s[1]
        )
        waypoint_distance = math.hypot(
            self.s_target[0] - s[0], self.s_target[1] - s[1]
        )
        return goal_distance + self.alpha * waypoint_distance

