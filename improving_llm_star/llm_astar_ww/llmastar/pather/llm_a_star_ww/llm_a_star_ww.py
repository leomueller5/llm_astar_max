"""LLM-A*-WW: LLM-A* with weighted waypoints.

Same input and output format as LLMAStar:

    planner = LLMAStarWW(llm="gpt", prompt="standard")
    result = planner.searching(query=query, filepath="temp.png")
    # result: {"operation": ..., "storage": ..., "length": ..., "llm_output": [...]}
"""
import heapq
import json
import math
import re

from llmastar.pather.llm_a_star.llm_a_star import LLMAStar
from llmastar.utils import list_parse

__all__ = ["LLMAStarWW"]


class LLMAStarWW(LLMAStar):
    """LLM-A* with weighted waypoints."""

    def __init__(self, llm="gpt", prompt="standard", weighting="los", switch_radius=3.0):
        super().__init__(llm=llm, prompt=prompt)
        assert weighting in ("los", "partial", "none")
        self.weighting = weighting
        self.switch_radius = switch_radius      # 0 = switching rule of LLM-A*
        self.waypoint_weights = []              # one weight per entry of target_list

    def _parse_query(self, query):
        # natural-language query: take the JSON part of the parser answer
        if isinstance(query, str):
            response = self.parser.chat(query) if self.llm == "gpt" else self.model.ask(query)
            match = re.search(r"\{.*\}", response, re.DOTALL)
            return json.loads(match.group(0) if match else response)
        return query

    def _parse_waypoints(self, response):
        # LLM waypoints, filtered as in LLM-A*; unparsable answer -> no waypoints
        try:
            nodes = list_parse(response)
            return self._filter_valid_nodes([(node[0], node[1]) for node in nodes])
        except Exception:
            return []

    def _visible(self, p, q):
        # straight segment p-q touches no barrier and no map border
        return p == q or not self.is_collision(p, q)

    def _weight_waypoints(self, nodes):
        # returns targets [start, ..., goal] and one weight per target
        start, goal = self.s_start, self.s_goal
        waypoints = [n for n in nodes if n != start and n != goal]

        if self.weighting == "none":
            targets = [start] + waypoints + [goal]
            return targets, [1.0] * len(targets)

        if self.weighting == "partial":
            targets, weights = [start], [1.0]
            for k, t in enumerate(waypoints):
                prev = targets[-1]
                if self._visible(prev, goal):
                    break
                nxt = waypoints[k + 1] if k + 1 < len(waypoints) else goal
                weight = 0.5 * self._visible(prev, t) + 0.5 * self._visible(t, nxt)
                if weight > 0:
                    targets.append(t)
                    weights.append(weight)
            return targets + [goal], weights + [1.0]

        # "los": line-of-sight validation
        points = [start] + waypoints + [goal]
        targets, i = [start], 0
        while i < len(points) - 1:
            j = next((j for j in range(len(points) - 1, i, -1) if self._visible(points[i], points[j])), None)
            if j is None or j == len(points) - 1:     # chain broken, or goal visible
                break
            targets.append(points[j])
            i = j
        targets.append(goal)
        return targets, [1.0] * len(targets)

    def _initialize_llm_paths(self):
        query = self._generate_llm_query(list(self.s_start), list(self.s_goal))
        if self.llm == "gpt":
            response = self.model.ask(prompt=query, max_tokens=1000)
        else:
            response = self.model.ask(prompt=query)
        self.llm_waypoints = self._parse_waypoints(response)
        self.target_list, self.waypoint_weights = self._weight_waypoints(self.llm_waypoints)
        self.i = 1
        self.s_target = self.target_list[1]

    def heuristic(self, s):
        # h(s) + alpha_t * cost(t, s) + (1 - alpha_t) * h(s)
        h = math.hypot(self.s_goal[0] - s[0], self.s_goal[1] - s[1])
        to_target = math.hypot(self.s_target[0] - s[0], self.s_target[1] - s[1])
        alpha = self.waypoint_weights[min(self.i, len(self.waypoint_weights) - 1)]
        return h + alpha * to_target + (1.0 - alpha) * h

    def _target_reached(self, s, s_n):
        if s_n == self.s_target:                     # rule of LLM-A*
            return True
        return (self.switch_radius > 0 and
                math.hypot(self.s_target[0] - s[0], self.s_target[1] - s[1]) <= self.switch_radius)

    def searching(self, query, filepath="temp.png"):
        self.filepath = filepath
        self._initialize_parameters(self._parse_query(query))
        self._initialize_llm_paths()

        self.PARENT[self.s_start] = self.s_start
        self.g[self.s_start] = 0
        heapq.heappush(self.OPEN, (self.f_value(self.s_start), self.s_start))

        goal_reached = False
        while self.OPEN:
            _, s = heapq.heappop(self.OPEN)
            self.CLOSED.append(s)
            if s == self.s_goal:
                goal_reached = True
                break
            for s_n in self.get_neighbor(s):
                if self.s_target != self.s_goal and self._target_reached(s, s_n):
                    self._update_target()            # next waypoint
                    self._update_queue()             # re-score OPEN
                if s_n in self.CLOSED:
                    continue
                new_cost = self.g[s] + self.cost(s, s_n)
                if s_n not in self.g:
                    self.g[s_n] = math.inf
                if new_cost < self.g[s_n]:
                    self.g[s_n] = new_cost
                    self.PARENT[s_n] = s
                    heapq.heappush(self.OPEN, (self.f_value(s_n), s_n))

        path = self.extract_path(self.PARENT) if goal_reached else []
        length = (sum(self._euclidean_distance(path[k], path[k + 1]) for k in range(len(path) - 1))
                  if path else math.inf)
        result = {"operation": len(self.CLOSED), "storage": len(self.g), "length": length,
                  "llm_output": self.target_list}
        if path:
            self.plot.animation(path, self.CLOSED, True, "LLM-A*-WW", self.filepath)
        return result
