# Добавляет в Android-проект виджет главного экрана: мост из приложения, сам виджет, разметку и запись в манифесте.
import os, re

BASE = 'android/app/src/main'
PKG_DIR = BASE + '/java/com/moyuniver/app'

def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write(text)

write(PKG_DIR + '/MainActivity.java', r'''package com.moyuniver.app;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(WidgetBridgePlugin.class);
        super.onCreate(savedInstanceState);
    }
}
''')

write(PKG_DIR + '/WidgetBridgePlugin.java', r'''package com.moyuniver.app;

import android.appwidget.AppWidgetManager;
import android.content.ComponentName;
import android.content.Context;
import android.os.Build;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/** Мост между приложением (страницей) и виджетом: страница присылает «снимок» данных, виджет его рисует. */
@CapacitorPlugin(name = "WidgetBridge")
public class WidgetBridgePlugin extends Plugin {

    @PluginMethod
    public void update(PluginCall call) {
        String json = call.getString("json");
        Context c = getContext();
        if (json != null) {
            c.getSharedPreferences(MoyWidgetProvider.PREFS, Context.MODE_PRIVATE).edit().putString("snap", json).apply();
            MoyWidgetProvider.refreshAll(c);
        }
        call.resolve();
    }

    @PluginMethod
    public void pin(PluginCall call) {
        Context c = getContext();
        boolean requested = false;
        try {
            AppWidgetManager m = AppWidgetManager.getInstance(c);
            if (Build.VERSION.SDK_INT >= 26 && m.isRequestPinAppWidgetSupported()) {
                requested = m.requestPinAppWidget(new ComponentName(c, MoyWidgetProvider.class), null, null);
            }
        } catch (Exception ignored) { }
        JSObject r = new JSObject();
        r.put("requested", requested);
        call.resolve(r);
    }
}
''')

write(PKG_DIR + '/MoyWidgetProvider.java', r'''package com.moyuniver.app;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.res.Configuration;
import android.os.Build;
import android.os.Bundle;
import android.util.TypedValue;
import android.view.View;
import android.widget.RemoteViews;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import org.json.JSONArray;
import org.json.JSONObject;

public class MoyWidgetProvider extends AppWidgetProvider {
    static final String PREFS = "moy_widget";
    private static final int MAX_ROWS = 6;
    private static final int[] ROW = {R.id.wI1, R.id.wI2, R.id.wI3, R.id.wI4, R.id.wI5, R.id.wI6};
    private static final int[] TXT_A = {R.id.wA1, R.id.wA2, R.id.wA3, R.id.wA4, R.id.wA5, R.id.wA6};
    private static final int[] TXT_B = {R.id.wB1, R.id.wB2, R.id.wB3, R.id.wB4, R.id.wB5, R.id.wB6};

    @Override
    public void onUpdate(Context c, AppWidgetManager m, int[] ids) {
        for (int id : ids) m.updateAppWidget(id, build(c, m, id));
    }

    /** Размер виджета изменили (потянули за рамку или повернули телефон): перестраиваем содержимое под новый размер. */
    @Override
    public void onAppWidgetOptionsChanged(Context c, AppWidgetManager m, int id, Bundle newOptions) {
        m.updateAppWidget(id, build(c, m, id));
    }

    public static void refreshAll(Context c) {
        AppWidgetManager m = AppWidgetManager.getInstance(c);
        int[] ids = m.getAppWidgetIds(new ComponentName(c, MoyWidgetProvider.class));
        for (int id : ids) m.updateAppWidget(id, build(c, m, id));
    }

    private static long dayStart(String dt) {
        try {
            Date d = new SimpleDateFormat("yyyy-MM-dd", Locale.US).parse(dt);
            Calendar c = Calendar.getInstance(); c.setTime(d); c.set(Calendar.HOUR_OF_DAY, 0); c.set(Calendar.MINUTE, 0); c.set(Calendar.SECOND, 0); c.set(Calendar.MILLISECOND, 0);
            return c.getTimeInMillis();
        } catch (Exception e) { return -1; }
    }

    /** Сколько дней до даты: меньше нуля — прошла. */
    private static int daysTo(String dt) {
        long a = dayStart(dt);
        if (a < 0) return 0;
        Calendar t = Calendar.getInstance(); t.set(Calendar.HOUR_OF_DAY, 0); t.set(Calendar.MINUTE, 0); t.set(Calendar.SECOND, 0); t.set(Calendar.MILLISECOND, 0);
        return (int) Math.round((a - t.getTimeInMillis()) / 86400000.0);
    }

    private static String dayLabel(String dt, boolean deadline) {
        int n = daysTo(dt);
        if (deadline) return n < 0 ? "просрочено" : n == 0 ? "сегодня" : n == 1 ? "завтра" : "через " + n + " дн.";
        if (n <= 0) return "";
        if (n == 1) return "завтра";
        try {
            Date d = new SimpleDateFormat("yyyy-MM-dd", Locale.US).parse(dt);
            return new SimpleDateFormat("EE d.MM", new Locale("ru")).format(d);
        } catch (Exception e) { return ""; }
    }

    private static int px(float dp, float density) { return Math.round(dp * density); }

    /** Размер этого виджета в dp (в портрете — ширина по минимуму и высота по максимуму, в ландшафте наоборот). */
    private static int[] sizeDp(Context c, AppWidgetManager m, int id) {
        int w = 250, h = 110;
        try {
            Bundle o = m.getAppWidgetOptions(id);
            if (o != null) {
                boolean land = c.getResources().getConfiguration().orientation == Configuration.ORIENTATION_LANDSCAPE;
                int ww = land ? o.getInt(AppWidgetManager.OPTION_APPWIDGET_MAX_WIDTH, 0) : o.getInt(AppWidgetManager.OPTION_APPWIDGET_MIN_WIDTH, 0);
                int hh = land ? o.getInt(AppWidgetManager.OPTION_APPWIDGET_MIN_HEIGHT, 0) : o.getInt(AppWidgetManager.OPTION_APPWIDGET_MAX_HEIGHT, 0);
                if (ww > 0) w = ww;
                if (hh > 0) h = hh;
            }
        } catch (Exception ignored) { }
        return new int[]{w, h};
    }

    static RemoteViews build(Context c, AppWidgetManager m, int id) {
        RemoteViews v = new RemoteViews(c.getPackageName(), R.layout.moy_widget);
        float dens = c.getResources().getDisplayMetrics().density;
        float fs = c.getResources().getConfiguration().fontScale;
        if (fs < 1f) fs = 1f;
        int[] sz = sizeDp(c, m, id);
        int wDp = sz[0], hDp = sz[1];

        String raw = c.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString("snap", null);
        boolean dark = false;
        String title = "Мой универ", empty = "Открой приложение, чтобы данные появились здесь", stale = "";
        List<String[]> rows = new ArrayList<>();
        if (raw != null) {
            try {
                JSONObject o = new JSONObject(raw);
                dark = "dark".equals(o.optString("theme"));
                title = o.optString("typeName", title);
                empty = o.optString("empty", empty);
                long now = System.currentTimeMillis();
                JSONArray a = o.optJSONArray("items");
                for (int i = 0; a != null && i < a.length() && rows.size() < 12; i++) {
                    JSONObject it = a.getJSONObject(i);
                    if (it.optLong("e") < now) continue;
                    boolean lesson = "lesson".equals(it.optString("k"));
                    String lab = dayLabel(it.optString("dt"), !lesson), sub = it.optString("b");
                    String second = lab.isEmpty() ? sub : (sub.isEmpty() ? lab : lab + " · " + sub);
                    rows.add(new String[]{it.optString("a"), second});
                }
                long gen = o.optLong("gen");
                if (gen > 0 && now - gen > 6L * 3600000L) stale = "данные от " + new SimpleDateFormat("HH:mm", Locale.getDefault()).format(new Date(gen));
            } catch (Exception ignored) { }
        }

        // ---- Подгонка под размер: сколько строк влезет, нужны ли вторые строки, какой шрифт ----
        boolean showTitle = hDp >= 80;
        int padV = hDp < 90 ? 8 : 14, padH = wDp < 150 ? 10 : 14;
        float aSp = wDp < 150 ? 13f : (wDp < 230 ? 14f : 15f), bSp = wDp < 150 ? 11f : 12f;
        float lineA = aSp * 1.35f * fs, lineB = bSp * 1.35f * fs;
        float titleH = showTitle ? 11f * 1.35f * fs + 4f : 0f;
        float footH = 10f * 1.35f * fs + 6f;
        float avail = hDp - 2 * padV - titleH;
        int total = rows.size();
        boolean showSub = true;
        float rowH = lineA + lineB + 6f;
        int cap = (int) Math.floor(avail / rowH);
        if (cap < 2 && total >= 3) {            // тесно: убираем вторые строки, если так влезет хотя бы три пункта вместо одного
            float rowH2 = lineA + 6f;
            int cap2 = (int) Math.floor(avail / rowH2);
            if (cap2 >= 3) { showSub = false; rowH = rowH2; cap = cap2; }
        }
        if (cap < 1) cap = 1;
        int shown = Math.min(Math.min(total, cap), MAX_ROWS);
        if (total > shown) {                    // часть не влезла: оставляем место под строку «ещё N»
            int cap3 = (int) Math.floor((avail - footH) / rowH);
            if (cap3 < 1) cap3 = 1;
            shown = Math.min(Math.min(total, cap3), MAX_ROWS);
        }
        int hidden = total - shown;
        String foot = "";
        if (hidden > 0) foot = "ещё " + hidden;
        if (!stale.isEmpty()) foot = foot.isEmpty() ? stale : foot + " · " + stale;

        int text = dark ? 0xFFF4ECEE : 0xFF1B1A2E, muted = dark ? 0xFFB39AA1 : 0xFF6D6B85;
        v.setInt(R.id.wRoot, "setBackgroundResource", dark ? R.drawable.moy_widget_bg_dark : R.drawable.moy_widget_bg_light);
        v.setViewPadding(R.id.wRoot, px(padH, dens), px(padV, dens), px(padH, dens), px(padV, dens));
        v.setViewVisibility(R.id.wTitle, showTitle ? View.VISIBLE : View.GONE);
        v.setTextViewText(R.id.wTitle, title.toUpperCase(new Locale("ru")));
        v.setTextColor(R.id.wTitle, muted);
        for (int i = 0; i < MAX_ROWS; i++) {
            if (i < shown) {
                String a = rows.get(i)[0], b = rows.get(i)[1];
                v.setViewVisibility(ROW[i], View.VISIBLE);
                v.setTextViewTextSize(TXT_A[i], TypedValue.COMPLEX_UNIT_SP, aSp);
                v.setTextViewTextSize(TXT_B[i], TypedValue.COMPLEX_UNIT_SP, bSp);
                if (showSub) {
                    v.setTextViewText(TXT_A[i], a);
                    v.setTextViewText(TXT_B[i], b);
                    v.setViewVisibility(TXT_B[i], b.isEmpty() ? View.GONE : View.VISIBLE);
                } else {
                    String head = b.split(" · ")[0];                 // время или «сегодня» — самое важное из второй строки
                    v.setTextViewText(TXT_A[i], head.isEmpty() ? a : head + "  " + a);
                    v.setViewVisibility(TXT_B[i], View.GONE);
                }
                v.setTextColor(TXT_A[i], text); v.setTextColor(TXT_B[i], muted);
            } else v.setViewVisibility(ROW[i], View.GONE);
        }
        v.setViewVisibility(R.id.wEmpty, rows.isEmpty() ? View.VISIBLE : View.GONE);
        v.setTextViewText(R.id.wEmpty, empty); v.setTextColor(R.id.wEmpty, muted);
        v.setTextViewTextSize(R.id.wEmpty, TypedValue.COMPLEX_UNIT_SP, wDp < 150 ? 12f : 14f);
        v.setTextViewText(R.id.wFoot, foot); v.setTextColor(R.id.wFoot, muted);
        v.setViewVisibility(R.id.wFoot, foot.isEmpty() ? View.GONE : View.VISIBLE);

        Intent open = c.getPackageManager().getLaunchIntentForPackage(c.getPackageName());
        if (open != null) {
            int flags = PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= 23 ? PendingIntent.FLAG_IMMUTABLE : 0);
            v.setOnClickPendingIntent(R.id.wRoot, PendingIntent.getActivity(c, 0, open, flags));
        }
        return v;
    }
}
''')

write(BASE + '/res/layout/moy_widget.xml', r'''<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:id="@+id/wRoot"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:padding="14dp">

    <TextView
        android:id="@+id/wTitle"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:maxLines="1"
        android:textSize="11sp"
        android:textStyle="bold" />

    <TextView
        android:id="@+id/wEmpty"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginTop="10dp"
        android:textSize="14sp"
        android:visibility="gone" />

    <LinearLayout android:id="@+id/wI1" android:layout_width="match_parent" android:layout_height="wrap_content" android:layout_marginTop="8dp" android:orientation="vertical">
        <TextView android:id="@+id/wA1" android:layout_width="match_parent" android:layout_height="wrap_content" android:maxLines="1" android:ellipsize="end" android:textSize="15sp" android:textStyle="bold" />
        <TextView android:id="@+id/wB1" android:layout_width="match_parent" android:layout_height="wrap_content" android:maxLines="1" android:ellipsize="end" android:textSize="12sp" />
    </LinearLayout>
    <LinearLayout android:id="@+id/wI2" android:layout_width="match_parent" android:layout_height="wrap_content" android:layout_marginTop="6dp" android:orientation="vertical">
        <TextView android:id="@+id/wA2" android:layout_width="match_parent" android:layout_height="wrap_content" android:maxLines="1" android:ellipsize="end" android:textSize="15sp" android:textStyle="bold" />
        <TextView android:id="@+id/wB2" android:layout_width="match_parent" android:layout_height="wrap_content" android:maxLines="1" android:ellipsize="end" android:textSize="12sp" />
    </LinearLayout>
    <LinearLayout android:id="@+id/wI3" android:layout_width="match_parent" android:layout_height="wrap_content" android:layout_marginTop="6dp" android:orientation="vertical">
        <TextView android:id="@+id/wA3" android:layout_width="match_parent" android:layout_height="wrap_content" android:maxLines="1" android:ellipsize="end" android:textSize="15sp" android:textStyle="bold" />
        <TextView android:id="@+id/wB3" android:layout_width="match_parent" android:layout_height="wrap_content" android:maxLines="1" android:ellipsize="end" android:textSize="12sp" />
    </LinearLayout>
    <LinearLayout android:id="@+id/wI4" android:layout_width="match_parent" android:layout_height="wrap_content" android:layout_marginTop="6dp" android:orientation="vertical">
        <TextView android:id="@+id/wA4" android:layout_width="match_parent" android:layout_height="wrap_content" android:maxLines="1" android:ellipsize="end" android:textSize="15sp" android:textStyle="bold" />
        <TextView android:id="@+id/wB4" android:layout_width="match_parent" android:layout_height="wrap_content" android:maxLines="1" android:ellipsize="end" android:textSize="12sp" />
    </LinearLayout>

    <LinearLayout android:id="@+id/wI5" android:layout_width="match_parent" android:layout_height="wrap_content" android:layout_marginTop="6dp" android:orientation="vertical">
        <TextView android:id="@+id/wA5" android:layout_width="match_parent" android:layout_height="wrap_content" android:maxLines="1" android:ellipsize="end" android:textSize="15sp" android:textStyle="bold" />
        <TextView android:id="@+id/wB5" android:layout_width="match_parent" android:layout_height="wrap_content" android:maxLines="1" android:ellipsize="end" android:textSize="12sp" />
    </LinearLayout>
    <LinearLayout android:id="@+id/wI6" android:layout_width="match_parent" android:layout_height="wrap_content" android:layout_marginTop="6dp" android:orientation="vertical">
        <TextView android:id="@+id/wA6" android:layout_width="match_parent" android:layout_height="wrap_content" android:maxLines="1" android:ellipsize="end" android:textSize="15sp" android:textStyle="bold" />
        <TextView android:id="@+id/wB6" android:layout_width="match_parent" android:layout_height="wrap_content" android:maxLines="1" android:ellipsize="end" android:textSize="12sp" />
    </LinearLayout>

    <TextView
        android:id="@+id/wFoot"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginTop="6dp"
        android:gravity="end"
        android:maxLines="1"
        android:textSize="10sp"
        android:visibility="gone" />
</LinearLayout>
''')

for name, color in (('light', '#FFFFFFFF'), ('dark', '#FF211519')):
    write(BASE + '/res/drawable/moy_widget_bg_%s.xml' % name, '''<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">
    <solid android:color="%s" />
    <corners android:radius="24dp" />
</shape>
''' % color)

write(BASE + '/res/xml/moy_widget_info.xml', r'''<?xml version="1.0" encoding="utf-8"?>
<appwidget-provider xmlns:android="http://schemas.android.com/apk/res/android"
    android:minWidth="250dp"
    android:minHeight="110dp"
    android:minResizeWidth="110dp"
    android:minResizeHeight="40dp"
    android:targetCellWidth="4"
    android:targetCellHeight="2"
    android:updatePeriodMillis="1800000"
    android:resizeMode="horizontal|vertical"
    android:widgetCategory="home_screen"
    android:description="@string/app_name"
    android:initialLayout="@layout/moy_widget" />
''')

# запись виджета в манифесте
mp = BASE + '/AndroidManifest.xml'
s = open(mp, encoding='utf-8').read()
if 'MoyWidgetProvider' not in s:
    receiver = '''
        <receiver android:name=".MoyWidgetProvider" android:exported="true" android:label="Мой универ">
            <intent-filter>
                <action android:name="android.appwidget.action.APPWIDGET_UPDATE" />
            </intent-filter>
            <meta-data android:name="android.appwidget.provider" android:resource="@xml/moy_widget_info" />
        </receiver>
'''
    assert '</application>' in s
    s = s.replace('</application>', receiver + '    </application>', 1)
    open(mp, 'w', encoding='utf-8').write(s)
print('виджет добавлен')
