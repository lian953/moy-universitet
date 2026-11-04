from PIL import Image
im = Image.open('icons/icon-512.png').convert('RGBA').resize((1024, 1024), Image.LANCZOS)
im.save('native/mobile/assets/icon-only.png')
im.save('native/mobile/assets/icon-foreground.png')
Image.new('RGBA', (1024, 1024), (240, 240, 246, 255)).save('native/mobile/assets/icon-background.png')
