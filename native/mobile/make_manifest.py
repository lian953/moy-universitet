# Разрешаем приложению принимать ссылку com.moyuniver.app:/oauth2redirect (возврат из входа Google)
p = 'android/app/src/main/AndroidManifest.xml'
s = open(p, encoding='utf-8').read()
flt = '''
            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="com.moyuniver.app" />
            </intent-filter>
'''
assert '</activity>' in s
if 'com.moyuniver.app" />' not in s:
    s = s.replace('</activity>', flt + '        </activity>', 1)
open(p, 'w', encoding='utf-8').write(s)
