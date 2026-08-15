import questionary

providers = {
            "Google AI Studio" : {
                "url": "https://generativelanguage.googleapis.com/v1beta/openai/",
                "key": "GOOGLE_API_KEY",
                "model": ["gemma-4-31b-it", "gemma-4-26b-a4b-it"]
            },
            "Open Router" : {
                "url": "https://openrouter.ai/api/v1",
                "key": "OPEN_ROUTER_KEY",
                "model": ["qwen/qwen3.5-flash-02-23", "dots-studio/dots-3-note-preview:free", "nvidia/nemotron-3-super-120b-a12b:free", "cohere/north-mini-code:free"]
            }
}   

class Profile():
     
    def __init__(self, mode, provider_url, model_name):
        self.mode = mode
        self.provider_name = "Unknown"
        self.provider_url = provider_url
        self.model_name = model_name
        self.key_name = "API_KEY"
        if model_name == "" or provider_url == "":
            self.provider_name = self.provider_selection()
            self.provider = providers.get(self.provider_name)
            self.model_name = self.model_selection()
            self.provider_url = self.provider.get('url')
            self.key_name =  self.provider.get('key')
        
    def provider_selection(self):
        selected = questionary.select(
            "Choose a Provider: ",
            choices=list(providers.keys())
        ).ask()
        if selected is None: raise
        return selected

    def model_selection(self):
        
        selected = questionary.select(
            "Select a Model: ",
            choices=self.provider.get("model")
        ).ask()
        if selected is None: raise
        return selected

