package org.evolware.bluelightmeter;

import android.app.Activity;
import android.util.Log;
import android.os.Bundle;
import android.view.View;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.content.pm.PackageManager;
import android.widget.Toast;
import org.evolware.bluelightmeter.BlueLightMeterDriver;
import org.evolware.bluelightmeter.BlueLightMeterData;

public class BlueLightMeterActivity extends Activity
{
    private static final String TAG = "BLMActivity";
    private BlueLightMeterData blmData;
    private BlueLightMeterDriver blmDriver;
    
    /** Called when the activity is first created. */
    @Override
    public void onCreate(Bundle savedInstanceState)
    {
	Log.i(TAG, "onCreate");
	super.onCreate(savedInstanceState);
        setContentView(R.layout.main);

	blmDriver = new BlueLightMeterDriver(this);
	blmData = blmDriver.getData();
	
        WebView mainWebView = (WebView) findViewById(R.id.mainWebView);

	// TODO: disable
	mainWebView.setWebContentsDebuggingEnabled(true);
	
        WebSettings webSettings = mainWebView.getSettings();
        webSettings.setJavaScriptEnabled(true);
     
        mainWebView.addJavascriptInterface(blmData, "BLM");
        mainWebView.setScrollBarStyle(View.SCROLLBARS_INSIDE_OVERLAY);
        mainWebView.loadUrl("file:///android_asset/blm.html");
    }

    // Connect and disconnect on Activity Resume/Pause to spare
    // battery on RFDuino.
    @Override
    public void onResume()
    {
	Log.i(TAG, "onResume");
	super.onResume();
	blmDriver.initDevice();
    }

    @Override
    public void onPause()
    {
	Log.i(TAG, "onPause");
	super.onPause();
	blmDriver.closeDevice();
    }
}
