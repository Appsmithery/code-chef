from huggingface_hub import HfApi

api = HfApi()
info = api.space_info('alextorelli/code-chef-modelops-trainer')
print(f'Stage: {info.runtime.stage}')
print(f'Hardware: {info.runtime.hardware}')
print(f'SDK: {info.sdk}')
print(f'Raw runtime: {info.runtime.raw}')
