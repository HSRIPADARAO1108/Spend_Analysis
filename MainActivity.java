package com.familymoney.tracker;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Bitmap;
import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.view.WindowManager;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.ProgressBar;
import android.widget.FrameLayout;

public class MainActivity extends Activity {

    // ====== CHANGE THESE TWO LINES TO YOUR STREAMLIT LINK ======
    private static final String APP_HOST = "YOUR-APP-NAME.streamlit.app";
    private static final String APP_URL  = "https://YOUR-APP-NAME.streamlit.app/?embed=true";
    // ===========================================================

    // true = hides the app in the recent-apps screen and blocks screenshots (extra privacy)
    private static final boolean PRIVACY_MODE = true;

    private WebView web;
    private ProgressBar bar;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (PRIVACY_MODE) {
            getWindow().setFlags(WindowManager.LayoutParams.FLAG_SECURE,
                    WindowManager.LayoutParams.FLAG_SECURE);
        }

        FrameLayout root = new FrameLayout(this);
        web = new WebView(this);
        bar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        bar.setLayoutParams(new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, 8));
        root.addView(web, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
        root.addView(bar);
        setContentView(root);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);          // Streamlit needs JavaScript
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(false);           // no access to phone files
        s.setAllowContentAccess(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        s.setGeolocationEnabled(false);
        s.setSupportMultipleWindows(false);

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
                Uri u = r.getUrl();
                boolean ours = "https".equals(u.getScheme()) && APP_HOST.equals(u.getHost());
                if (ours) return false;                       // stay inside the app
                try {                                         // everything else -> normal browser
                    startActivity(new Intent(Intent.ACTION_VIEW, u));
                } catch (Exception ignored) { }
                return true;
            }
            @Override
            public void onPageStarted(WebView v, String url, Bitmap f) { bar.setVisibility(View.VISIBLE); }
            @Override
            public void onPageFinished(WebView v, String url) { bar.setVisibility(View.GONE); }
        });

        if (savedInstanceState == null) web.loadUrl(APP_URL);
        else web.restoreState(savedInstanceState);
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        web.saveState(out);
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) web.goBack();
        else super.onBackPressed();
    }
}
