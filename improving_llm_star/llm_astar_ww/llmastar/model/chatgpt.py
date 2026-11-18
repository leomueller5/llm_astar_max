import os

# Updated for openai>=1.0 and GPT-4o mini. The original wrapper used the legacy completion API with
# gpt-3.5-turbo-instruct and stopped every answer at the first newline, which cuts off multi-line
# answers. The API key is read from the environment variable OPENAI_API_KEY; the model can be changed
# with LLM_ASTAR_MODEL (default: gpt-4o-mini).


class ChatGPT:
    def __init__(self, method, sysprompt, example, model=None):
        self.id = 0
        self.model = model or os.environ.get("LLM_ASTAR_MODEL", "gpt-4o-mini")
        self._client = None
        self.chat_history = [
            {"role": "system", "content": sysprompt}
        ]
        if example:
            self.prompt = sysprompt + f'\nFollow these examples delimited with “”" as a guide.\n'
            for key in list(example.keys()):
                input = example[key]
                index = input.find("\n") + 1
                self.prompt += f'“”"\nUser: {input[:index - 1]}\nAssistant: {input[index:]}“”"\n'
                self.chat_history.append({"role": "user", "content": input[:index - 1]})
                self.chat_history.append({"role": "assistant", "content": input[index:]})
        else:
            self.prompt = sysprompt

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(max_retries=5)          # reads OPENAI_API_KEY
        return self._client

    def ask(self, prompt, stop=None, max_tokens=1000):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=max_tokens,
            stop=stop,
        )
        return response.choices[0].message.content or ""

    def chat(self, query, prompt="", stop=None, max_tokens=1000):
        messages = [{"role": "system", "content": self.prompt},
                    {"role": "user", "content": query}]
        if prompt:
            messages.append({"role": "assistant", "content": prompt})
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0,
            max_tokens=max_tokens,
            stop=stop,
        )
        return response.choices[0].message.content or ""

    def chat_with_image(self, chat_history, stop=None, max_tokens=1000):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=chat_history,
            temperature=0,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
