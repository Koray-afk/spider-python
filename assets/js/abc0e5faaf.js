//$Id$
class messageboardsdk{
    constructor(domainID,orgId,messagepanel_iconId){
        this.serviceId=domainID.serviceid;
        this.orgId=orgId;
        this.domain=domainID.inproductdomain;
        this.messagepanel_iconId=document.getElementById(messagepanel_iconId);
        this.customizePanelStyle();
        this.customizeMessageStyle();
        this.setOnClickCallback();
    }
  
    customizePanelStyle(panelstyle={}){
        this.panelJson=panelstyle;
    }
  
    customizeMessageStyle(messagestyle={}){
        this.styleJson=messagestyle;
    }
  
    customizeStyles(styles={}){
        if(Object.keys(styles).length > 1){
            styles.messageStyle?this.customizeMessageStyle(styles.messageStyle):'';
            styles.panelStyle?this.customizePanelStyle(styles.panelStyle):'';
        }
    }
  
    setOnClickCallback(funcName){
        this.callback=funcName;
    }
  
    changeOrg(orgID)
    {   if(this.mics_iframe){
        this.messagepanel_iconId.style["pointer-events"] = "none";
        this.messagepanel_iconId.style.opacity = this.panelJson.panelIconOpacity || "0.4";
        document.getElementById("stackedNumber").style.display = 'none';
        this.iconDisabled = true;
        this.mics_iframe.contentWindow.postMessage({
            "type": "orgUpdate",
            "orgID": orgID
        },this.domain);
    }
    }
  
    updateMessageStyle(styleJSON) {
        if(this.mics_iframe){
        this.mics_iframe.contentWindow.postMessage({
            "type": "styleUpdate",
            "styles": styleJSON
        },this.domain);
    }
    }
    initialize(){
        if(Inproductutility.isInproductinbundle()){
            return;
        }
        this.urlsrc="https://"+document.domain+"/mics/analytics/stacked.jsp?frameorigin=https://"+document.domain;
         let domaincopy=this.domain;
        var tipdomaingroupname=(domaincopy.includes('tipengine.')?'tipengine.':(domaincopy.includes('tipengine1.')?'tipengine1.':(domaincopy.includes('tipengine2.')?'tipengine2.':'tipengine3.')));
        var tipDomain=this.domain.split('//')[1].replace(tipdomaingroupname, "").split('.').reverse();
        var domainCheck=(document.domain).split('.').reverse();
        domainCheck=domainCheck.slice(0,tipDomain.length).join('');
        tipDomain=tipDomain.join('');
        if(tipDomain===domainCheck){
            this.urlsrc=this.domain+"/analytics/stacked.jsp?frameorigin=https://"+document.domain;
        }
    else{
    this.domain="https://"+document.domain;    
    }
        (this.messagepanel_iconId).innerHTML += '<span style="display:none" id="stackedNumber" >0</span>';
        this.messagepanel_iconId.style["pointer-events"] = "none";
        if (this.messagepanel_iconId.style.opacity >= 1 || this.messagepanel_iconId.style.opacity == "") {
            this.messagepanel_iconId.style.opacity = this.panelJson.panelIconOpacity||"0.2";
        }
        this.mics_iframeDiv = document.createElement("div");
        this.mics_iframeDiv.id = "mics_stacked_carpet";
        this.panelJson.iframePosition =='left' ? this.mics_iframeDiv.className = "micsPanelLeft": this.mics_iframeDiv.className = "micsPanelRight";
        this.mics_iframe = document.createElement("iframe");
        this.mics_iframe.id="micsiframe";
        this.mics_iframe.setAttribute("sandbox", "allow-scripts allow-same-origin");
        this.stacked_backdrop = document.createElement("div");
        this.stacked_backdrop.id = "mics_stacked_backdrop";
    (!(this.panelJson.backdropPaddingTop)&&(this.panelJson.backdropPaddingBottom))?(this.panelJson.backdropPaddingTop="0px"):(((this.panelJson.backdropPaddingTop)&&!(this.panelJson.backdropPaddingBottom))?(this.panelJson.backdropPaddingBottom="0px"):"");
    (!(this.panelJson.panelPaddingTop)&&(this.panelJson.panelPaddingBottom))?(this.panelJson.panelPaddingTop="0px"):(((this.panelJson.panelPaddingTop)&&!(this.panelJson.panelPaddingBottom))?(this.panelJson.panelPaddingBottom="0px"):"");
    this.stacked_backdrop.setAttribute("style","background:"+(this.panelJson.backdropColor||'#000')+";z-index:"+ (this.panelJson.backdropZindex||9999)+";height:"+('calc( 100vh - ('+ (this.panelJson.backdropPaddingTop + " + " + this.panelJson.backdropPaddingBottom) +'))'||'')+";top:"+(this.panelJson.backdropPaddingTop||'')+";bottom:"+(this.panelJson.backdropPaddingBottom||''));
    this.mics_iframeDiv.setAttribute("style","height:"+('calc( 100vh - ('+ (this.panelJson.panelPaddingTop + " + " + this.panelJson.panelPaddingBottom) +'))'||'')+";z-index:"+ (this.panelJson.panelZindex||99999)+";top:"+(this.panelJson.panelPaddingTop||'')+";bottom:"+(this.panelJson.panelPaddingBottom||''));
        this.stacked_backdrop.style.background=this.panelJson.backdropColor||"#000";        
        document.body.append(this.stacked_backdrop);
        document.body.append(this.mics_iframeDiv);
        this.mics_iframeDiv.append(this.mics_iframe);
        var stackedURI = window.location.protocol + "//" + window.location.hostname + (window.location.port ? ':' + window.location.port : '');
        var styleJson = this.styleJson || {};
        var handle = this;
        var loadSuccess = false;
        this.iconDisabled = true;
        var reloadTime = 5 * 60;
        var panelname=this.panelJson.panelTemplateName || "panel-template-primary";
        var reloadIFrame = function(reloadTime){
             setTimeout(function() {
                if (loadSuccess == false) {
                    handle.mics_iframe.src = handle.urlsrc || "/analytics/stacked.jsp";
                    reloadIFrame((reloadTime * 2) < 3600 ? (reloadTime * 2) : 3600);
                }
              }, reloadTime * 1000);
          }
        reloadIFrame(reloadTime);
        this.mics_iframe.onload = function(e) {
            handle.mics_iframe.contentWindow.postMessage({
                "type": "init",
                "serviceID": handle.serviceId,
                "orgID": handle.orgId,
                "url": stackedURI,
                "panelId": 1,
                "panelTemplateName": panelname,
                "styles": styleJson
              },handle.domain);
        };
  
        this.mics_iframe.src =handle.urlsrc || "/analytics/stacked.jsp";
        window.addEventListener("message", function(event, a, b) {
            // if(event.data.emittype == 'messageboardMsgFromWms'){
            //     handle.mics_iframe.contentWindow.postMessage({ "emittype": "wmscallback", "msg": event.data.msg }, handle.domain);
            // }
            // if(event.data.emittype == 'messageboardServerupFromWms'){
            //     handle.mics_iframe.contentWindow.postMessage({ "emittype": "Bannerwmscallbackserver", "serverup": event.data.serverup }, handle.domain);
            // }
            if (event.origin !=handle.domain) {
                    return;
            }
        if (event.data.panelId == 1) {
                switch (event.data.type) {
                    case "open":
                        handle.onclick(event.data);
                        break;
                    case "close":
                        handle.stacked_backdrop.click();
                        break;
                    case "start-tour":
                        //console.log("received in parent")
                        handle.startTour(event.data);
                    case "notification":
                        if (loadSuccess == false || handle.iconDisabled) {
                            handle.messagepanel_iconId.style["pointer-events"] = "all";
                            handle.messagepanel_iconId.style.opacity = "1";
                            loadSuccess = true;
                            handle.iconDisabled = false;
                            }
                        handle.updateNumber(event.data);
                        break;
                    case "save-flow":
                        
                        window.localStorage.setItem(event.data.flowID,JSON.stringify(event.data.flowdata));
                        break;
                    case "loadwalkthroughflow":
                        WalkthroughSDK.getInstance().loadFlow([event.data.flowID],'Service')
                        break;
                    case "reload":
                        loadSuccess = false;
                        handle.iconDisabled = true;
                        reloadIFrame(reloadTime);
                        handle.messagepanel_iconId.style["pointer-events"] = "none";
                        handle.messagepanel_iconId.style.opacity = this.panelJson.panelIconOpacity || "0.4";
                        break;
                  }
              }
       });
  
      this.messagepanel_iconId.addEventListener('click', function() {
                if (!handle.mics_iframe.src) {
                    handle.mics_iframe.src =handle.urlsrc || "/analytics/stacked.jsp";
                    }
          if(handle.stacked_backdrop.style.display!=='block'){
                handle.stacked_backdrop.style.display = 'block';
                handle.mics_iframeDiv.style.display = 'block';
                handle.updateNumber({
                    "value": {
                        "unviewedMessages": 0
                      }
                });
                handle.mics_iframe.contentWindow.postMessage({
                    "type": "focus"
                },handle.domain);}
          else{
        handle.stacked_backdrop.click();
          }
              });
  
      this.stacked_backdrop.addEventListener('click', function() {
                handle.stacked_backdrop.style.display = 'none';
                handle.mics_iframeDiv.style.display = 'none';
                handle.mics_iframe.contentWindow.postMessage({
                  "type": "backdrop"
                },handle.domain);
         }, false);
      
     
 
      this.updateNumber= function (data) {
            var no = data.value.unviewedMessages;
            var indicatorID=document.getElementById("stackedNumber");
            indicatorID.className=this.panelJson.messageIndicator==="number"?"micsnumber":"micsdot";
            (+no > 0)?(indicatorID.style.display = 'block') & (indicatorID.innerHTML = no):indicatorID.style.display = 'none';
            if(this.panelJson.messageIndicatorStyle){
              var indicatestyle=this.panelJson.messageIndicatorStyle;
              indicatestyle.backGround?indicatorID.style.background=indicatestyle.backGround:"";
              this.panelJson.messageIndicator==='number'?(indicatestyle.color?indicatorID.style.color=indicatestyle.color:""):"";
              indicatestyle.bottom?indicatorID.style.bottom=indicatestyle.bottom:"";
              indicatestyle.top?indicatorID.style.top=indicatestyle.top:"";
              indicatestyle.left?indicatorID.style.left=indicatestyle.left:"";
              indicatestyle.right?indicatorID.style.right=indicatestyle.right:"";
              indicatestyle.fontSize?indicatorID.style.fontSize=indicatestyle.fontSize:"";
              indicatestyle.borderRadius?indicatorID.style.borderRadius=indicatestyle.borderRadius:"";
            }
    };        
        this.onclick= function (data) {
            if(this.callback){
                return this.callback(data);
            }
            if(data.value.ctaType=='walkthrough')
            {
                this.startTour(data);
                return;
            }
            var link = data.value.cta;
            var a = document.createElement('a');                                                                                                        
            a.setAttribute("referrerpolicy", "no-referrer");
            a.href = link;
            a.target = "_blank";
            document.body.appendChild(a);
            a.click();
        },
        this.startTour=function (data) {
            WalkthroughSDK.getInstance().triggerFlow(data.value.cta,'messageboard',data.value.PID,'Service');
        }
    }
  };
/*$Id$*/
class bannersdk {
    static instance = null;
    constructor(inproductconf,orgID,appID='',clientportalID='',orgType=null) {
    this.inproductconf=inproductconf;
    this.orgID=orgID;
    this.serviceID=inproductconf.serviceid;
    this.url=inproductconf.inproductdomain;
    this.appID=appID;   
    this.clientportalID=clientportalID;
    this.isparentSdk = window.self == window.top;
    this.orgmodeltype=orgType;
    this.bannerbuffertime=3600000;
    this.wmsenabled = true;
    this.pollingenabled = true;
    this.scope="Service";
    this.provisionvsproduct={'mics':'0','dap':'1'};
    this.provisionarray=['mics','dap']; 
    this.verification=false;
    this.verificationcontent={};
    this.createDivforIframe();
    this.postmessagelistener= VerificationMessageListener.initialiseListener();
    this.inproductcommunicationListener ={};
    this.helphubinitialise=null;
    this.walkthroughinitialise=null;
    this.enablemoduleconf={};
    this.setStyleforHelphubPlaceholder = function(){};
    this.setStyleforHelphubPopup = function(){};
    this.setHelphubContent = function(){};
    this.changeHelphubPlaceholder = function(){};
    this.workspaceconf={};
    this.setinsession("orgID",this.orgID);
    this.pollingverifybanner= false;
    this.lastpolltime=Date.now();
    this.setinsession("inproductconf",JSON.stringify(this.inproductconf));
    this.localstoragemanager=new bannersdklocalstoragemanager();
    this.localstoragemanager.reservespaceforORG(orgID);
    this.tipOrgID=null;
    this.localstoragemanager.setCallbackListenser("micssdkstorage", this.callbackforlocalstorageupdate, this);
    this.micssdktoserver = Micssdktoserver.getinstance(this.inproductconf, this.orgID, "banner");
    this.activeWorkspaceconf = {};

    }

    getprovisiontype() {
        return this.provisionarray.map(productname => this.provisionvsproduct[productname]).filter(code => code !== undefined).join(',');
    }
    
    disableprovisioning(product){
        var productname = product.toLowerCase();
        if(this.provisionarray.includes(productname)){
            this.provisionarray = this.provisionarray.filter(item => item !== productname);
            this.provisiontype = this.provisionarray.join(',');
        }
    }

    setappid(appID,orgType){
        this.appID = appID;
        this.setorgmodeltype(orgType);
        Inproductutility.setAppID(appID);
    }
    
    setclientportalid(clientportalID,orgType){
        this.clientportalID = clientportalID;
        this.setorgmodeltype(orgType);
        Inproductutility.setClientPortalID(clientportalID);
    }

    setorgmodeltype(orgType){
        this.orgmodeltype = orgType;
        Inproductutility.setOrgModelType(orgType);
    }

    setclientportalandappid(clientportalID,appID,orgType){
        this.setappid(appID,orgType);
        this.setclientportalid(clientportalID,orgType);
    }
    getCDN_version(){
        try {
            var inproductscripturl =  [...document.scripts].find(s =>
                /micsinproduct\/.*\/inproductsdk\.js/.test(s.src)
              ).src;
            var urlObj = new URL(inproductscripturl);
            var parts = urlObj.pathname.split("/").filter(Boolean);
            return  {
                domain: urlObj.origin,
                bucketname: parts[0],
                version: parts[1],
                filename : parts[2]
                };

        } catch (error) {
            return {}
        }
    }
    enablemicse() {
        this.scope = "Enterprise";
    }
    constructorQueryParam(params){
        var paramskeys = Object.keys(params);
        return Micssdktoserver.instance.getQueryParam(paramskeys,params,false);
    }
    setverifydata(message) {
        if (this.tipDiv.innerHTML != '') {
           return
        }
        //check if banner has walkthrough;
        this.isWalkthroughBanner(message);
        this.setVideoConf(message);
        this.verification = true;
        this.verificationcontent = message;
        this.drawTip(message);
    }
    setinsession(key, value) {
        var micsconf = JSON.parse(sessionStorage.getItem("micsinproduct")) || {};
        micsconf[key] = value;
        sessionStorage.setItem("micsinproduct", JSON.stringify(micsconf));
    }
    getinsession(key) {
        var micsconf = JSON.parse(sessionStorage.getItem("micsinproduct")) || {};
        return micsconf[key];
    }
    setinlocal(key, value) {
        localStorage.setItem(key, JSON.stringify(value));
    }
    getinlocal(key) {
        return this.bannersdk_parseJSON(localStorage.getItem(key));
    }   
    isWalkthroughBanner(message) {
        if (JSON.parse(message).iswalkthroughbanner) {
            this.workspaceconf = JSON.parse(message).workspaceconf;
            this.initializewalkthrough();
        }
    }
    setVideoConf(msg) {
        let json = this.bannersdk_parseJSON(msg);
        json.videoConf ? this.enablemoduleconf.videoConf = json.videoConf : '';
    }
    setpolltimeforlonginterval(handle){
        document.addEventListener("visibilitychange", () => {
            if (document.visibilityState === "visible") {
                var lastpollingtime = this.getinlocal("micslastpolltime");
                if((Date.now() - (+lastpollingtime)) > 900000){
                    var pollingdetail={type:"bannerimmediatepoll"};
                    handle.postmessagetoiframe(pollingdetail,handle.url);
                }
            } 
          });
    }
    checkstatsinLS(handle){
        var lsreserveid=handle.getlsreserveid(handle);
        var statswithbanner = handle.localstoragemanager.getMetrics(lsreserveid);
        var tipOrgID = handle.localstoragemanager?.micssdkstorage?.banner?.[lsreserveid]?.[0]?.data?.tipOrgID;
        this.tipOrgID =tipOrgID?tipOrgID: handle.orgID;
        var statsvaluesid={"received":2,"clicked":3,"closed":4};
        if(statswithbanner.stats.length > 0){
            for(let statsvalue of statswithbanner.stats){
                handle.postmessagetoiframe( {"promotionID":statswithbanner.bannerid,"feedback":statsvaluesid[statsvalue],"scope":statswithbanner.scope},handle.url);
            }
        }
    }

    initialize(){
        if(Inproductutility.isInproductinbundle()){
            return;
        }
        bannersdk.instance = this;
        var handle=this;
        handle.localstoragemanager.reservespaceforORG(handle.getlsreserveid(handle));
        this.inproductcommunicationListener = InproductMsgListener.initialiseListener(this.inproductconf, this.orgID);
        function testFlexbox () {
            var f = 'flex';
            var fw = '-webkit-flex';
            var el = document.createElement('b');
            
          try {
              el.style.display = fw;
              el.style.display = f;
              return !!(el.style.display === f || el.style.display === fw );
            } catch (err) {
                return false;
            }
        }
        function supportsCss(p) {
            var b = document.body || document.documentElement,
            s = b.style;
            
            if (typeof s[p] == 'string') { return true; }
            
            var v = ['Moz', 'webkit', 'Webkit', 'Khtml', 'O', 'ms'];
            p = p.charAt(0).toUpperCase() + p.substr(1);
            
            for (var i=0; i<v.length; i++) {
                if (typeof s[v[i] + p] == 'string') { return true; }
            }
            
            return false;
        }
        function checkForMobile(){
            var isMobile = false;
            if(/(android|bb\d+|meego).+mobile|avantgo|bada\/|blackberry|blazer|compal|elaine|fennec|hiptop|iemobile|ip(hone|od)|ipad|iris|kindle|Android|Silk|lge |maemo|midp|mmp|netfront|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\/|plucker|pocket|psp|series(4|6)0|symbian|treo|up\.(browser|link)|vodafone|wap|windows (ce|phone)|xda|xiino/i.test(navigator.userAgent) 
            || /1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\-(n|u)|c55\/|capi|ccwa|cdm\-|cell|chtm|cldc|cmd\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\-s|devi|dica|dmob|do(c|p)o|ds(12|\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\-|_)|g1 u|g560|gene|gf\-5|g\-mo|go(\.w|od)|gr(ad|un)|haie|hcit|hd\-(m|p|t)|hei\-|hi(pt|ta)|hp( i|ip)|hs\-c|ht(c(\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\-(20|go|ma)|i230|iac( |\-|\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\/)|klon|kpt |kwc\-|kyo(c|k)|le(no|xi)|lg( g|\/(k|l|u)|50|54|\-[a-w])|libw|lynx|m1\-w|m3ga|m50\/|ma(te|ui|xo)|mc(01|21|ca)|m\-cr|me(rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\-2|po(ck|rt|se)|prox|psio|pt\-g|qa\-a|qc(07|12|21|32|60|\-[2-7]|i\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\-|oo|p\-)|sdk\/|se(c(\-|0|1)|47|mc|nd|ri)|sgh\-|shar|sie(\-|m)|sk\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\-|v\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\-|tdg\-|tel(i|m)|tim\-|t\-mo|to(pl|sh)|ts(70|m\-|m3|m5)|tx\-9|up(\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|yas\-|your|zeto|zte\-/i.test(navigator.userAgent.substr(0,4))){ isMobile = true;}
            return isMobile;
        }
        
        if(!testFlexbox()||checkForMobile()||!supportsCss('transition')||!supportsCss('transform')){
            return;
        }
        var delay=(new Date().getTime()-localStorage.getItem("micsnotificationtime"+handle.serviceID))<30000?5000:500; //No I18n
        localStorage.setItem("micsnotificationtime"+handle.serviceID,new Date().getTime());  //No I18n
        handle.timestamp=new Date().getTime();
        localStorage.setItem("micsTabSwitchTime",handle.timestamp);
        handle.urlsource="https://"+document.domain+"/mics";
        let domaincopy=handle.url;
        var tipdomaingroupname=(domaincopy.includes('tipengine.')?'tipengine.':(domaincopy.includes('tipengine1.')?'tipengine1.':(domaincopy.includes('tipengine2.')?'tipengine2.':'tipengine3.')));
        var tipDomain=handle.url.split('//')[1].replace(tipdomaingroupname, "").split('.').reverse();
        var domainCheck=(document.domain).split('.').reverse();
        domainCheck=domainCheck.slice(0,tipDomain.length).join('')
        tipDomain=tipDomain.join('');
        if(tipDomain===domainCheck){
                handle.urlsource=handle.url;
                handle.domainType  = 'zoho';
            }
        else{
            handle.domainType  = domainCheck.includes('manageengine') ? "manageengine" : '' ;
            handle.url="https://"+document.domain;
        }
        var query={
            "ORGID":handle.orgID,
            "ServiceID":handle.serviceID,
            "polling":true,
            "frameorigin":handle.domain ,
            "Feedback":handle.version,
            "Scope":handle.scope,
            "provisiontype":handle.getprovisiontype(),
            "isparentSdk":handle.isparentSdk,
            "appID":handle.appID,
            "clientportalID":handle.clientportalID,
            "orgtype":handle.orgmodeltype

        }
        let queryParam = handle.constructorQueryParam(query);
        this.timer=setInterval(function(){ handle.iframe.setAttribute("src",handle.urlsource+"/Notification"+queryParam); },this.failTimeout);
        setTimeout(function(){ handle.iframe.setAttribute("src",handle.urlsource+"/Notification"+queryParam); },delay);
            //comment1
        var bannerinlocastorage=handle.localstoragemanager.checkbannerinlocalstorage(handle.getlsreserveid(handle));
        if(bannerinlocastorage){
            //initialize WalkthroughSDK and render Banner.
            handle.workspaceconf=handle.getWalkthroughConf();
            handle.initializewalkthrough();
            handle.drawTip(bannerinlocastorage);
        }
        handle.setinlocal('micslastpolltime',handle.lastpolltime);
        handle.setpolltimeforlonginterval(handle);
    }
    setWalkthroughConf(configuration){
        let workspaceconf ={};
        workspaceconf[this.orgID]=configuration;
        this.setinlocal('workspaceconf',workspaceconf);
    }
    getWalkthroughConf(){
        let workspaceconf = this.getinlocal('workspaceconf')|| {};
        return workspaceconf[this.orgID]|| {};
    }
    createDivforIframe(){
    this.userData={};
    this.version=3;
    var tip=this;
    if (!window.location.origin) {
        window.location.origin = window.location.protocol + "//" + window.location.hostname + (window.location.port ? ':' + window.location.port: '');
    }
    this.domain=location.origin;
    this.failTimeout=7200000;
    this.displayTimeout=220;
    this.tipDiv=document.createElement("div");
    this.tipDiv.setAttribute("id","mics_tipDiv");
    this.backdrop=document.createElement("div");
    this.backdrop.setAttribute("id","micsbackdrop"); 
    this.backdrop.setAttribute("class","micshide");
    this.iframeDiv=document.createElement("div");
    this.iframe=document.createElement("iframe");
    this.iframe.setAttribute("sandbox","allow-scripts allow-same-origin");
    this.iframeDiv.setAttribute("style","position:absolute;top:100px;left:-30005%;display:none");
    this.iframeDiv.appendChild(this.iframe);
    this.tpDiv=document.createElement("div");
    this.tpDiv.setAttribute("id","mics_tpDiv");
    this.tpDiv.setAttribute("class","micshide");  
    this.tipDiv.setAttribute("class","micshide");
    document.body.prepend(this.iframeDiv,this.tipDiv,this.backdrop,this.tpDiv);
    var handle=this;
    this.userDataString="";
    this.timestamp=new Date().getTime();
    Object.keys(this.userData).forEach(function(d){ handle.userDataString+=("&"+d+"="+handle.userData[d]);  });
    window.addEventListener("message", function(event,a,b){
        if(event.origin===handle.url){
            if(event.data&&event.data!=="None"&&event.data.type!=="tabSwitch"){
                tip.drawTip(event.data);
            }
            else if(event.data.type==="tabSwitch"){
                if(!event.data.IsActive){
                    handle.tipDiv.setAttribute("class","micshide");
                    handle.eraseBanner(handle.tipDiv);
                }                
            }
            if (typeof event.data === "string" && JSON.parse(event.data).Timeout && !(JSON.parse(event.data).PromotionID)) {
                handle.pollingenabled = false;
            }
        }
        if(Inproductutility.validatePostMessageOrigin(event, "sameDomain")){
            switch (event.data.type) {
                 case "buffertime":
                    handle.bannerbuffertime=event.data.bannerbuffertime;
                    handle.checkstatsinLS(handle);
                    break;
                case "micsresize":
                    Array.prototype.forEach.call(handle.tipDiv.getElementsByClassName("micsiframe"),function (d) {
                    d.setAttribute("style", "width:" + event.data.width + ";height:" + event.data.height);});
                    break;
                case "micsclose":
                    Array.prototype.forEach.call(handle.tipDiv.getElementsByClassName("micsclose"),function (d) {
                        d.click();});
                    break;
                case "micsclick":
                    handle.promotionClicked();
                    break;
                case "workspaceconf":
                    handle.workspaceconf = event.data.configuration;
                    break;
                case "initialise":
                    handle.enablemoduleconf = event.data;
                    handle.initialiseinproductmodules();
                    break;
                case "getinproducturl":
                    var staticurlconf = handle.getCDN_version();
                    event.source.postMessage({ type: "inproducturl", url: staticurlconf }, event.origin);
                    break;
                default:
                    break;
            }
        }
        if(sessionStorage.getItem("bannerverifydata")){
            handle.setverifydata(handle.bannersdk_parseJSON(sessionStorage.getItem("bannerverifydata")));
            sessionStorage.removeItem("bannerverifydata");
        }
    });
}
    initialiseinproductmodules() {
        for (let modules in this.enablemoduleconf.moduleConf) {
            if (this.enablemoduleconf.moduleConf[modules]) {
                this.modulefinder(modules);
            }
        }
    }
    modulefinder(modules) {
        switch (modules) {
            case "helphub":
            case "checklist":
                this.initializewalkthrough();
                this.initializehelphub(this.enablemoduleconf.moduleConf);
                break;
            case "walkthrough":
                this.initializewalkthrough();
                break;
            default:
                break;
        }
    }
    initializehelphub(moduleConf) {
        var handle = this;
        if(!selfhelpsdk.instance){
            handle.helphubinitialise = new RequestContentWrapper(handle.inproductconf, handle.orgID);
            handle.helphubinstance = handle.helphubinitialise;
            handle.helphubinitialise.moduleVisibility = {
                helphubVisible: moduleConf && moduleConf.helphub,
                checklistVisible: moduleConf && moduleConf.checklist
            };
            handle.helphubinitialise.selfhelpcontents.tabswitch = {
                helphubdata: moduleConf && moduleConf.helphub,
                taskdata: moduleConf && moduleConf.checklist
            };
            handle.setStyleforHelphubPlaceholder = handle.helphubinitialise.setStyleforHelphubPlaceholder;
            handle.setStyleforHelphubPopup = handle.helphubinitialise.setStyleforHelphubPopup;
            handle.setHelphubContent = handle.helphubinitialise.setHelphubContent;
            handle.changeHelphubPlaceholder = handle.helphubinitialise.changeHelphubPlaceholder;
            handle.helphubinitialise.domainConf = handle.enablemoduleconf.videoConf;
             handle?.enablemoduleconf?.helphubstyle && handle.helphubinitialise.updateStyleConfig(handle.enablemoduleconf.helphubstyle);
            handle.helphubinitialise.urlUtil.setUrlValidationConf(handle.enablemoduleconf.urlValidationConf)
            handle.helphubinitialise.domainConf.domainType = handle.domainType;
            if (!handle.helphubinitialise.moduleVisibility.helphubVisible && !handle.helphubinitialise.moduleVisibility.checklistVisible) {
                return;
            }
            handle.helphubinitialise.initialize();
        }
    };
    initializewalkthrough() {
        this.setWalkthroughConf(this.workspaceconf);
        let instance;
        if (WalkthroughSDK.getInstance()) {
            //WalkthroughSDK.getInstance().setDynamicConf(this.workspaceconf);
            instance = WalkthroughSDK.getInstance();
        } else {
            instance = new WalkthroughSDK(this.inproductconf, this.orgID);
            this.walkthroughinitialise = instance;
        }
        instance.urlUtil.setUrlValidationConf(this.enablemoduleconf?.urlValidationConf);
        // instance.setDynamicConf(this.workspaceconf);
        instance.setupSdk(this.enablemoduleconf);
        (instance.workspaceconf && Object.keys(instance.workspaceconf).length > 0) ? " " : instance.setworkspaceconf(this.workspaceconf);

        this.walkthroughinitialise ? this.walkthroughinitialise.initialize() : '';
    };
    drawThirdParty(url,width,height,data){
        var handle=this;
        data=data?data:{};
        this.tpDiv.classList.remove("micshide");  //No I18n
        this.backdrop.classList.remove("micshide");  //No I18n
        this.backdrop.setAttribute("style",data.tpbackdropStyle?data.tpbackdropStyle:"");
        handle.eraseBanner(this.tpDiv);
        this.tpiframe=document.createElement("iframe");
        this.tpLoading=document.createElement("div");
        this.tpLoading.setAttribute("class",data.tploadingClass?data.tploadingClass:" micsloading");
        this.tpLoading.setAttribute("style",data.tploadingStyle?data.tploadingStyle:"");
        this.tpDiv.appendChild(this.tpLoading);
        this.tpDiv.appendChild(this.tpiframe);
        this.tpiframe.onload=function(){ if(handle.tpLoading.parentNode===handle.tpDiv){ handle.tpDiv.removeChild(handle.tpLoading); }  }
        this.tpiframe.setAttribute("src",url);
        this.tpiframe.setAttribute("sandbox","allow-forms allow-scripts");
        this.tpDiv.setAttribute("style",data.tpStyle?data.tpStyle:("width:"+width+"%;height:"+height+"%;top:"+(parseInt((100-height)/2))+"%;left:"+(parseInt((100-width)/2))+"%;padding:50px;"));
        this.tpiframe.setAttribute("style",data.tpiframe?data.tpiframeStyle:('width:100%;height:100%'));
        var close=document.createElement("span");close.setAttribute("class","mics_tpclx clx");
        close.setAttribute("style",data.tpcloseStyle?data.tpcloseStyle:"");
        this.tpDiv.insertBefore(close,this.tpDiv.childNodes[0]);
        close.addEventListener("click",function(){
            handle.tpDiv.setAttribute("class","micshide");
            handle.backdrop.setAttribute("class","micshide");
            handle.eraseBanner(handle.tpDiv);
        //comment2
        });
    }
    drawTip(data){
        var handle=this;
        clearInterval(handle.timer);
        var tipData1=handle.bannersdk_parseJSON(data);
        var tipData=handle.bannersdk_parseJSON(tipData1.NDETAILS);
        if(tipData1.module==='banner'){
         handle.lastpolltime=Date.now();
         handle.setinlocal('micslastpolltime',handle.lastpolltime);
         if((tipData1.PromotionID==undefined||tipData1.PromotionID==''||tipData1.PromotionID==null) && handle.localstoragemanager.checkbannerloadtimeonly(handle.getlsreserveid(handle)) && !handle.verification) {
            handle.eraseBanner(handle.tpDiv);
            handle.eraseBanner(handle.tipDiv);
            handle.localstoragemanager.dequeMessage(handle.getlsreserveid(handle));
            return
        }
    }
        if(tipData1.PromotionID==undefined||tipData1.PromotionID==''||tipData1.PromotionID==null||handle.tipDiv.innerHTML!==""){
            //no need to enter without pid and already content in banner.
            return;
        }
        handle.tipOrgID=tipData1.tipOrgID?tipData1.tipOrgID:handle.orgID;
        tipData1.workspaceConf ? handle.activeWorkspaceconf = tipData1.workspaceConf : "";
        handle.pollingverifybanner=tipData.isVerification||false;
        if(!handle.verification && !handle.pollingverifybanner){
        if(!handle.localstoragemanager.getbannerloadtimeinlocalstorage(handle.getlsreserveid(handle),tipData1.PromotionID)){
            return;
        }
    handle.localstoragemanager.enqueMessage(handle.getlsreserveid(handle),tipData1,handle.bannerbuffertime);
        }
        handle.pid=tipData1.PromotionID;
        handle.scopeName=tipData1.scope;
        handle.zuid=tipData1.ZUID?tipData1.ZUID:0;
        if(handle.verification){ //Dev should note that => for verification checking alone
        if(handle.pid>-1){
                return;
            }
            handle.eraseBanner(handle.tipDiv);
        }
        if(this.pid===localStorage.getItem("micsnotificationid"+handle.serviceID+""+handle.scopeName) && !handle.verification){
            handle.postmessagetoiframe( {"promotionID":handle.pid,"feedback":4,"scope":handle.scopeName} ,handle.url);     //No I18n
        }
        if(this.pid===localStorage.getItem("micsnotificationid"+handle.serviceID+""+handle.scopeName)||handle.tipDiv.innerHTML!==""||!tipData.type && !handle.verification){
            return;
        }
        if(!handle.verification){
            handle.updatestatinlocalstorage("received",true,this.pid);
            this.postmessagetoiframe({"promotionID":this.pid,"feedback":2,"scope":handle.scopeName},this.url);  //No I18n
        }
        function getBgUrl(el) {
            var bg = "";
            if (el.currentStyle) { // IE
                bg = el.currentStyle.backgroundImage;
            } else if (document.defaultView && document.defaultView.getComputedStyle) { // Firefox
                bg = document.defaultView.getComputedStyle(el, "").backgroundImage;
            } else { // try and get inline style
                bg = el.style.backgroundImage;
            }
            if(bg == "none")
            {
                return "";
            }
            var backgroundUrl = bg.replace(/url\(['"]?(.*?)['"]?\)/i, "$1").split(",")[0];
            
            return backgroundUrl;
        }
        switch (tipData.type) {
            case "banner":
                handle.tipDiv.removeAttribute("style");
                handle.tipDiv.setAttribute("style", decodeURI(tipData.style));
                handle.tipDiv.setAttribute("class", tipData.className + " bannerhide");
                var test = document.createElement("img");
                test.addEventListener('load', function () { handle.drawBanner(tipData, handle, handle.pid); });
                test.addEventListener('error', function () { handle.drawBanner(tipData, handle, handle.pid); });
                test.setAttribute("src", getBgUrl(handle.tipDiv));
                break;
            case "customizedhtmlBanner":
                handle.drawCustomHTMLBanner(tipData, handle);
                break;
            case "htmlBanner":
                handle.drawHTMLBanner(tipData, handle);
                break;
            case "customwebbanner":
            case "desktopbanner":
                handle.drawCustomHTMLBanner(tipData, handle);
                break;
            default:
                // Handle default case if needed
                break;
        }
    }
    drawCustomHTMLBanner(tipData, handle) {
        handle.promotionID = handle.pid;
        handle.scopenamefrombanner = handle.scopeName;
        handle.tipDiv.removeAttribute("style");
        handle.tipDiv.innerHTML = "";
        handle.tipDiv.classList.remove("micshide");
        var layoutDiv = document.createElement("div");
        layoutDiv.setAttribute("id", "micsshadowContainer");
        handle.tipDiv.appendChild(layoutDiv);
        var shadowdom = layoutDiv.attachShadow({ mode: "closed" });
        shadowdom.innerHTML = `<style>${tipData.css}</style>${tipData.html}`;
        if (handle.verification) {
            handle.bannerverification({ status: "deliver" });
        }
        var addMICSbannerClickListener = function (selector, callback) {
            Array.from(shadowdom.querySelectorAll(selector)).forEach(function (element) {
                var linkType = element.getAttribute("linkvalue");
                if (linkType != 'walkthrough' && linkType != 'web url' && linkType != 'salesiq widget') {
                    var linkType = element.getAttribute("linktype");
                }
                if (linkType == 'walkthrough') {
                    var flowID = element.getAttribute("linkvalue");
                    var WalkthroughSDKInstance = WalkthroughSDK.getInstance();
                    if (WalkthroughSDKInstance == null) {
                        return;
                    }
                    WalkthroughSDKInstance.loadFlow([flowID], handle.scopenamefrombanner);
                    element.addEventListener('click', () => {
                        handle.promotionClicked();
                        WalkthroughSDKInstance.triggerFlow(flowID, "banner", handle.promotionID, handle.scopenamefrombanner);
                    })
                }
                else {
                    element.addEventListener("click", () => callback(element));
                }
            });
        };
        addMICSbannerClickListener(".close", function () { handle.promotionClosed(); });
        addMICSbannerClickListener(".cta_button", function (ctaButton) {
            var linkValue = ctaButton.getAttribute("linktype");
            var buttonlinktype = linkValue;
            switch (linkValue) {
                case "walkthrough":
                case "web url":
                    linkValue = ctaButton.getAttribute("linkvalue");
                    break;
                case "salesiq widget":
                        window.$zoho=window.$zoho || {}; 
                        window.$zoho.salesiq=window.$zoho.salesiq || {ready:function(){}};;
                        var script = document.createElement('script');
                        script.id = 'zmsiqscript';
                        script.src = ctaButton.getAttribute("linkvalue");
                        script.defer = true;
                        script.onload =function() {
                            if (window.$zoho && $zoho.salesiq  ) {

                                siqwidegetopen();
                            }
                        };
                        function siqwidegetopen(){
                            if($zoho.salesiq.floatwindow){
                                $zoho.salesiq.floatwindow.visible('show');
                            }else{
                                setTimeout(siqwidegetopen,1000);
                            }
                        }
                        document.body.appendChild(script);
                    break;
                case "Interactivevideo":
                case "guide":
                case "desktopinteractivevideo":
                case "desktopguide":
                    var materialId = ctaButton.getAttribute("linkvalue");
                    var videoconf = handle.enablemoduleconf.videoConf;
                    var materialType = {
                        desktopinteractivevideo: "interactivevideo",
                        desktopguide: "guide"
                    }[linkValue.toLowerCase()] || linkValue.toLowerCase();
                    var domain = "https://" + (videoconf.domain[handle.domainType] ? videoconf.domain[handle.domainType] : document.domain);
                    linkValue =
                    domain +
                    (handle.scopeName == "Enterprise"
                        ? '/dap/' +
                        materialType + '/' +
                        videoconf.servicename + '/' +
                        (handle.activeWorkspaceconf.workspaceID || videoconf.workspaceid) + '/' +
                        materialId +
                        ((handle.promotionID !== undefined && handle.promotionID !== -1)
                            ? '/' + handle.promotionID
                            : '/preview')
                        : '/mics/' +
                        materialType + '/' +
                        videoconf.servicename + '/' +
                        materialId
                    );
                    break;
                case "externalContent":
                    var materialId = ctaButton.getAttribute("linkvalue");
                    var videoconf = handle.enablemoduleconf.videoConf;
                    var materialType = "externallink"
                    var domain = "https://" + (videoconf.domain[handle.domainType] ? videoconf.domain[handle.domainType] : document.domain);
                    linkValue =
                    domain +
                    (handle.scopeName == "Enterprise"
                        ? '/dap/' +
                        materialType + '/' +
                        videoconf.servicename + '/' +
                        (handle.activeWorkspaceconf.workspaceID || videoconf.workspaceid) + '/' +
                        materialId +
                        ((handle.promotionID !== undefined && handle.promotionID !== -1)
                            ? '/' + handle.promotionID
                            : '/preview')
                        : '/mics/' +
                        materialType + '/' +
                        videoconf.servicename + '/' +
                        materialId
                    );
                    break;
                default:
                    break;
            }
            if(buttonlinktype != 'salesiq widget'){
                window.open(linkValue, "_blank");
            }
            handle.promotionClicked();
        });
        //script import
        this.importscript(tipData,shadowdom,runScriptCallback);
     
        function runScriptCallback(shadowdom) {
         try {
            micsShadowDomReference(shadowdom);
        }
        catch (err) { }
        }
    }
    importscript(tipData,shadowdom,runScriptCallback){
        var version = tipData.version;
        var script = document.createElement('script');
        if (version == undefined) {
            script.innerHTML = tipData.script;
            shadowdom.appendChild(script);
            runScriptCallback(shadowdom);
        } else if (version >= 2) {
            script.src = tipData.script_src;
            script.onload = () => { runScriptCallback(shadowdom); }
            shadowdom.appendChild(script);
        };
    }
    bannersdk_parseJSON(str) {
        try {
            return JSON.parse(str);
        } catch (e) {
            return {};
        }
    }
    drawHTMLBanner(tipData, handle) {
        this.promotionID = handle.pid;
        this.scopenamefrombanner = handle.scopeName;
        handle.tipDiv.removeAttribute("style");
        handle.tipDiv.innerHTML = "";
        handle.tipDiv.classList.remove("micshide");
        var layoutDiv = document.createElement("div");
        layoutDiv.setAttribute("id", "micsshadowContainer");
        handle.tipDiv.appendChild(layoutDiv);
        var shadowdom = layoutDiv;
        shadowdom = shadowdom.attachShadow({ mode: "closed" });
        shadowdom.innerHTML = "<style>" + tipData.css + "</style>" + tipData.html;
        var script = document.createElement('script');
        script.innerHTML = tipData.script;
        shadowdom.appendChild(script);
        activateScript(shadowdom);
        Array.prototype.forEach.call(shadowdom.querySelectorAll(".cta_button"), function (d) { //No I18n
            d.addEventListener("click", function (event) {
                handle.promotionClicked();
            });
        });
        Array.prototype.forEach.call(shadowdom.querySelectorAll(".close"), function (d) { //No I18n
            d.addEventListener("click", function (event) {
                handle.promotionClosed();
                clearBanner(event);
            });
        });
    }
    drawBanner(data,par,pid){
        var image=document.createElement("span");image.setAttribute("class","micsimage");
        var box=document.createElement("div");box.setAttribute("class","micsBox");
        var img=document.createElement("img");image.appendChild(img);
        var content=document.createElement("span");content.setAttribute("class","micscontent");
        var inner=document.createElement("span");inner.setAttribute("class","micsinner");
        var action=document.createElement("span");action.setAttribute("class","micsaction");
        var close=document.createElement("span");close.setAttribute("class",data.close.className?data.close.className:"micsclose");
        var toggle=document.createElement("span");toggle.setAttribute("class",data.hide.className?data.hide.className:"micstoggle");
        var iframeDiv=document.createElement("div");iframeDiv.setAttribute("class","micsiframeDiv");
        var iframe=document.createElement("iframe");iframe.setAttribute("class","micsiframe");
        iframeDiv.appendChild(iframe);
        var handle=this;
        this.promotionID=pid;
        this.scopenamefrombanner=handle.scopeName;
        this.iframeSrc = data.iframeSrc;
        toggle.addEventListener("click",function(e){
                  handle.tipDiv.classList.add("micshidden"); //No I18n
                handle.tipDiv.classList.add("micswrap"); //No I18n
                  e.stopPropagation();
                });
            handle.tipDiv.addEventListener("click",function(){
                if ( (" " + handle.tipDiv.className + " ").replace(/[\n\t]/g, " ").indexOf("micshidden") > -1 ){
                    handle.tipDiv.classList.remove("micshidden"); //No I18n
                    setTimeout(function(){   handle.tipDiv.classList.remove("micswrap");   },handle.displayTimeout);
                }
            });
            close.addEventListener("click",function(){
                if(data.iframeSrc){
                    iframe.contentWindow.postMessage( {"type":"micsClose"} ,data.iframeSrc);
                }
                handle.postmessagetoiframe( {"promotionID":pid,"feedback":4,"scope":handle.scopenamefrombanner},handle.url);  //No I18n
                handle.tipDiv.classList.add("bannerhide");
                if(handle.wmsenabled){
                    handle.pollingenabled = true;
                    handle.postmessagetoiframe({ "emittype": "Bannerwmspoll"},handle.url);
                }
          setTimeout(function(){   handle.tipDiv.classList.add("micshide"); handle.eraseBanner(handle.tipDiv);   },handle.displayTimeout);
                handle.eraseBanner(handle.tpDiv);
                handle.updatestatinlocalstorage("closed",true);
          //comment2
        });
        var pdata=this.parseData(data.content,content,inner);
        var iframeScrolling=data.iframeScrolling?data.iframeScrolling:"auto";
        iframeDiv.setAttribute("style",data.iframeDivStyle);
        iframe.setAttribute("frameborder",0);iframe.setAttribute("marginwidth",0);
        iframe.setAttribute("marginheight",0);iframe.setAttribute("scrolling",iframeScrolling);
        function loadiframe(){
            if(data.iframeSrc){
                iframe.addEventListener("load",function(){   
                    handle.tipDiv.setAttribute("class",data.className);
                    iframe.contentWindow.postMessage( {"type":"userData","zuid":handle.zuid,"orgID":handle.orgID,"userData":handle.userData,"scope":handle.scopenamefrombanner} ,data.iframeSrc);
                });
                if(data.iframesdk){
                    iframe.setAttribute("src",data.iframeSrc+((data.iframeSrc.indexOf('?')!=-1)?"&":"?")+"orgID="+handle.orgID+"&zuid="+handle.zuid+handle.userDataString);
                }
                else{
                    iframe.setAttribute("src",data.iframeSrc);
                }
            }
            else{
                iframeDiv.setAttribute("style","display:none;");
                handle.tipDiv.setAttribute("class",data.className);
            }
        }
        img.setAttribute("style", decodeURI(data.image.style));
        iframe.setAttribute("style", data.iframeStyle);
        image.setAttribute("style", decodeURI(data.imageStyle));
        box.setAttribute("style", decodeURI(data.boxStyle));
        inner.setAttribute("style", decodeURI(data.innerStyle));
        content.setAttribute("style", decodeURI(data.contentStyle));
        action.setAttribute("style", decodeURI(data.actionStyle));
        close.setAttribute("style", decodeURI(data.close.style));
        toggle.setAttribute("style", decodeURI(data.hide.style));
        action.appendChild(toggle);
        action.appendChild(close);
        handle.eraseBanner(this.tipDiv);
        box.appendChild(image);
        content.appendChild(inner);
        content.appendChild(iframeDiv);
        box.appendChild(content);
        box.appendChild(action);
        this.tipDiv.appendChild(box);
        img.addEventListener('load', function() {    loadiframe();    });
        img.addEventListener('error', function() {        loadiframe();   });
        img.setAttribute("src",data.image.src);
        Array.prototype.forEach.call(content.getElementsByClassName("micsSameLink"),function(d){ //No I18n
            d.addEventListener("click",function(){
                handle.postmessagetoiframe({"promotionID":pid,"feedback":3,"scope":handle.scopenamefrombanner},handle.url); //No I18n
                handle.drawThirdParty(this.getAttribute("url"),this.getAttribute("urlWidth"),this.getAttribute("urlHeight"),data.iframedata);
                handle.updatestatinlocalstorage("clicked",true);
            });
        });
        Array.prototype.forEach.call(content.getElementsByClassName("micsNewLink"),function(d){ //No I18n
            d.addEventListener("click",function(){
                handle.promotionClicked();
            });
        });
    }
    bannerverification(msg) {
        VerificationCompleteMessager.notifySuccess("banner", msg);
    }
    promotionClicked(){
        var handle = this;
        if(handle.verification){
            handle.bannerverification({ status: "clicked" });
            return;
        }
        handle.postmessagetoiframe({"promotionID":this.promotionID,"feedback":3,"scope":handle.scopenamefrombanner},handle.url);
        handle.updatestatinlocalstorage("clicked",true);
    }
    promotionClosed(){
        var handle = this;
        if(handle.verification){
           handle.eraseBanner(handle.tipDiv);
           handle.bannerverification({ status: "closed" });
           return;
        }
        handle.postmessagetoiframe({"promotionID":this.promotionID,"feedback":4,"scope":handle.scopenamefrombanner},handle.url); //No I18n
        handle.eraseBanner(handle.tipDiv);
        //comment2
        handle.updatestatinlocalstorage("closed",true);
    }
    parseData(data, div, inner) {
        var handle = this;
        function createElement(ele, className, dv) {
            var element = document.createElement(ele);
            element.setAttribute("class", className);
            dv.appendChild(element);
            return element;
        }
        data.forEach(function (d) {
            switch (d.type) {
                case "link": //No I18n
                    if (d.sdk) {
                        d.link = d.link + ((d.link.indexOf('?') != -1) ? "&" : "?") + "orgID=" + handle.orgID + "&zuid=" + handle.zuid + handle.userDataString;
                    }
                    if (d.check) {
                        var celem = createElement("a", "micsSameLink micslink", inner);
                        celem.setAttribute("url", d.link);
                        celem.setAttribute("urlheight", d.height ? d.height : 100);
                        celem.setAttribute("urlwidth", d.width ? d.width : 100);
                        celem.innerText = d.text;
                        celem.setAttribute("style", decodeURI(d.style));
                    }
                    else {
                        var celem = createElement("a", "micsNewLink micslink", inner);
                        if (d.flowID) {
                            WalkthroughSDK.getInstance().loadFlow(d.flowID, handle.scopenamefrombanner)
                            celem.addEventListener('click', () => { WalkthroughSDK.getInstance().triggerFlow(d.flowID, "banner", handle.promotionID, handle.scopenamefrombanner) })
                        }
                        else {
                            celem.setAttribute("href", d.link);
                            celem.setAttribute("target", "_blank");
                        }
                        celem.innerText = d.text;
                        celem.setAttribute("style", decodeURI(d.style));
                    }
                    break;
                case "desc": //No I18n
                    var celem = createElement("span", "micsdesc", inner); celem.innerText = d.text; celem.setAttribute("style", decodeURI(d.style));
                    break;
                case "header": //No I18n
                    var celem = createElement("span", "micsheader", div); celem.innerText = d.text; celem.setAttribute("style", decodeURI(d.style));
                    break;
            }
        });
    }  

    getlsreserveid(handle=this){
        return handle.orgID+handle.appID+handle.clientportalID;
    }

    bannerstatshandler(bannerdata, instance) {
        var lsreserveid=instance.getlsreserveid(instance);
        const bannerObj = bannerdata.banner?.[lsreserveid]?.[0];
        if (!bannerObj ||(typeof bannerObj === "object" && Object.keys(bannerObj).length === 0)) {
          instance.eraseBanner(instance.tipDiv);
          return;
        } 
        const promotionID = bannerObj.data?.PromotionID;
        switch (instance.localstoragemanager.checkbannersendstats(lsreserveid, promotionID)) {
          case "load":
          case "received":
            instance.drawTip(JSON.stringify(bannerObj.data));
            break;
          case "clicked":
          case "closed":
            instance.eraseBanner(instance.tipDiv);
            break;
          default:
            break;
        }
     }

    updatestatinlocalstorage(key,value,pid=this.promotionID){
        if (document.visibilityState === 'visible' && !this.pollingverifybanner){
        this.localstoragemanager.updateMetrics(this.getlsreserveid(),pid,key,value);
        }
    }

    callbackforlocalstorageupdate(updatedbanner, instance){
        instance.bannerstatshandler(updatedbanner, instance);
    }

    postmessagetoiframe(message,iframedomain){
        if (document.visibilityState === 'visible' && !this.verification){
            //adding tipOrgID;
            message["tipOrgID"] = this.tipOrgID;
            this.iframe.contentWindow.postMessage(message,iframedomain);
        }
    }
    eraseBanner(parent) {
        while (parent.firstChild) {
          parent.removeChild(parent.firstChild);
        }
        parent.className = 'micshide';
      }
};

//$Id$
class SdkAutoinitializer {
    constructor(config) {
      this.initialised = false;
      this.walkthroughinstance='';
      this.helphubinstance='';
      this.config = config;
    }

    initializeHelphub() {
      var handle = this;
      if(!selfhelpsdk.instance){
        this.initializeWalkthrough(this.config);
        handle.helphubinstance = new selfhelpsdk(this.config.inproductconf, this.config.orgid);
       handle.helphubinstance = new RequestContentWrapper(handle.inproductconf, handle.orgID);
        handle.setStyleforHelphubPlaceholder = handle.helphubinstance.setStyleforHelphubPlaceholder;
        handle.setStyleforHelphubPopup = handle.helphubinstance.setStyleforHelphubPopup;
        handle.setHelphubContent = handle.helphubinstance.setHelphubContent;
        handle.changeHelphubPlaceholder = handle.helphubinstance.changeHelphubPlaceholder;
        handle.helphubinstance.domainConf = this.config.videoConf;
        handle.helphubinstance.urlUtil.setUrlValidationConf(this.config.urlValidationConf);
        handle.helphubinstance.domainConf.domainType = this.config.domainType;
        handle.helphubinstance.initialize();
        return;
      }
      handle.helphubinstance.urlUtil.setUrlValidationConf(this.config.urlValidationConf);
  
  };

  initializeWalkthrough() {

      if (WalkthroughSDK.getInstance()) {
          WalkthroughSDK.getInstance().setworkspaceconf(this.config.workspaceconf);
          WalkthroughSDK.getInstance().urlUtil.setUrlValidationConf(this.config.urlValidationConf);
          return;
      };
      this.walkthroughinstance = new WalkthroughSDK(this.config.inproductconf, this.config.orgid);
      this.walkthroughinstance.urlUtil.setUrlValidationConf(this.config.urlValidationConf);
      this.walkthroughinstance.setworkspaceconf(this.config.workspaceconf);
      this.walkthroughinstance.initialize();
  };
  }//$Id$
class VerificationMessageListener {
    static listener = null;
    constructor() {
        this.inproducttypevslistenerinstance = {
            "selfhelp": SelfHelpVerificationMessageListener,
            "checklist": SelfHelpVerificationMessageListener,
            "banner": BannerVerificationMessageListener,
            "messageboard": MessageBoardVerificationMessageListener,
            "walkthrough": WalkthroughVerificationMessageListener,
        };
        this.seteventlistener();
        this.notifyReferrer();
    }

    static initialiseListener() {
        if (VerificationMessageListener.listener === null) {
            VerificationMessageListener.listener = new VerificationMessageListener();
        }
        return;
    }


    seteventlistener() {
        var handle = this;
        window.addEventListener("message", function (payload) {
            if (payload.data.source === "micsinproduct" && payload.data.type != 'readytoverify' && payload.data.type != "walkthrough") {
                if (!Inproductutility.validatePostMessageOrigin(payload, "openerDomain")) return;
                var inproducttype = payload.data.type.toLowerCase();    /* Type = banner/messageboard/selfhelp/walkthrough */
                var instance = handle.inproducttypevslistenerinstance[inproducttype]
                if ((inproducttype === 'selfhelp' || inproducttype === 'checklist') && payload.data.message) {
                    payload.data.message.type = inproducttype;
                }
                instance.processMessage(payload.data.message);
            }
        });
    }

    notifyReferrer() {
        if (window.opener != null && Inproductutility.validatePostMessageOrigin({origin: document.referrer}, "openerDomain") ) {
            window.opener.postMessage(
                { source: "micsinproductsdk", type: 'readytoverify' }, document.referrer);

        }
    }
}


class SelfHelpVerificationMessageListener {

    static processMessage(message) {
        if(message.isAutoInitializeSDK){
            var sdkAutoInitializer = new SdkAutoinitializer(message);
            sdkAutoInitializer.initializeHelphub();
            sdkAutoInitializer.helphubinstance.setverifydata(message);    
        }
        else{
            if (selfhelpsdk.instance) {
                var sdkinstance = selfhelpsdk.instance;
                sdkinstance.setverifydata(message);
                return
            }
            sessionStorage.setItem("selfhelpverifydata", JSON.stringify(message));
    }
    }

}

class MessageBoardVerificationMessageListener {
    static processMessage(message) {

    }
}
class WalkthroughVerificationMessageListener {
    static processMessage(message) {
        if (WalkthroughSDK.instance) {
            var sdkinstance = WalkthroughSDK.instance;
            if (message.pid === 'smarttour') {
                sdkinstance.startsmarttour(message);
                return;
            }
            sdkinstance.setverifydata(message);
            return
        }
        sessionStorage.setItem("walkthroughsdkdata", JSON.stringify(message));
    }
}
class BannerVerificationMessageListener {
    static processMessage(message) {
        if (bannersdk.instance) {
            var sdkinstance = bannersdk.instance;
            sdkinstance.setverifydata(message);
            return;
        }
        sessionStorage.setItem("bannerverifydata", JSON.stringify(message));
    }
}




class VerificationCompleteMessager {

    static notifySuccess(inproducttype, msg) {
        if (window.opener ) {
            window.opener.postMessage({ "type": 'verify', "inproducttype": inproducttype, "source": "micsinproductsdk", "message": msg ? msg : msg = { status: "success" } }, document.referrer);
        }   
    }


}
//  $Id$
class Micssdktoserver{
    static instance=null;
    static callbackIdcounter=0;
    static dap_product_type = "";
    constructor(inproductconf, orgID) {
        this.orgID = orgID;
        this.domain = inproductconf.inproductdomain;
        this.serviceid = inproductconf.serviceid;
        this.mediumvsclass=new Map();
        this.mediumvsclass.set("banner",BannerAPI);
        this.mediumvsclass.set("messageboard",MessageboardAPI);
        this.mediumvsclass.set("walkthrough",WalkthroughAPI);
        this.mediumvsclass.set("selfhelp",SelfhelpAPI);
         this.mediumvsclass.set("helprequest", HelpRequestAPI);
        this.callbacks={};
        this.apistack=[];
        this.Isinproductframeloaded=false;
        this.isCustomdomain=true;
        this.iframeWindow=this.initializeframe();
        Micssdktoserver.instance=this;
        this.inproductListener();
    }
 
    static getinstance(inproductconf, orgID, medium){
        if(Micssdktoserver.instance){
            return new (Micssdktoserver.instance.mediumvsclass.get((medium).toLowerCase()))();
        }
        new Micssdktoserver(inproductconf,orgID);
        return new (Micssdktoserver.instance.mediumvsclass.get((medium).toLowerCase()))();
    }
 
    static callApi(medium, api_type, endpoint, method, apiconfig, requestheaders, clientparams, onsuccess, onerror,async){
        let callbackId=-1;
        if(onsuccess||onerror){
            callbackId = Micssdktoserver.callbackIdcounter++;
            Micssdktoserver.instance.callbacks[callbackId] = {'onsuccess': onsuccess, 'onerror': onerror};
        }
        var params={};
    
        var inproductConf = Inproductutility.getInproductConf();
        clientparams = { ...inproductConf, ...clientparams };
        params["queryParam"]=Micssdktoserver.instance.getQueryParam(apiconfig.queryparams,clientparams);
        params["bodyParam"]=Micssdktoserver.instance.getBodyParam(apiconfig.bodyparams,clientparams);
 
        if(Micssdktoserver.instance.isCustomdomain){
            endpoint="/mics" + endpoint
        }
 
    var content={"data":{
            "medium":medium,
            "http_method":(method.toLowerCase()),
            "queryParam":params["queryParam"],
            "bodyParam":params["bodyParam"],
            "api":endpoint,
            "api_type":api_type,
            "callbackId":callbackId,
            "requestheaders":requestheaders,
            "async":async,
            "micsinproduct":true
        },"domain":Micssdktoserver.instance.domainUrl};
 
        if(Micssdktoserver.instance.Isinproductframeloaded){
    Micssdktoserver.makecalltoframe(content);
    }
    else{
        Micssdktoserver.instance.apistack.push(content);    
    }
    }
    
    static makecalltoframe(content){
    document.getElementById("micssdktoserverIframe").contentWindow.postMessage(content.data,content.domain);
 
    }
 
 
    initializeframe() {
        if(Inproductutility.isInproductinbundle()){
            return;
        }
        var self=this;
        this.domainUrl = location.origin + "/mics/jsp/inproduct.jsp?frameorigin=" + location.origin;
        
        var domain = this.domain.split('//')[1].replace("tipengine.", "").split('.').reverse();
        var domainCheck = (location.hostname).split('.').reverse();
        domainCheck = domainCheck.slice(0, domain.length).join('');
        domain = domain.join('');
        if (domain === domainCheck) {
            this.domainUrl = this.domain + "/jsp/inproduct.jsp?frameorigin=" + location.origin;
            this.isCustomdomain=false;
        }
 
        this.iframewindow = document.createElement('iframe');
        this.iframewindow.setAttribute("sandbox","allow-scripts allow-same-origin");
        this.iframewindow.setAttribute("src", this.domainUrl);
        this.iframewindow.setAttribute("style", "position: absolute; width:0; height:0; border:0");
        this.iframewindow.setAttribute("id", "micssdktoserverIframe");
        document.body.append(this.iframewindow);
        return this.iframewindow;
    }
 
    inproductListener(){
        var handle=this;
        window.addEventListener('message',(event)=>{
        if(!Inproductutility.validatePostMessageOrigin(event, "sameDomain")) return;
        let data = event.data;
        if(data.type=="inproductresponse"){
            let callback = handle.callbacks[data.callbackId];
            data.callback_type=="success"?callback.onsuccess(data.response):callback.onerror(data.response);
            delete handle.callbacks[data.callbackId];
            }
    else if(data.type=="inproductiframeload"){
        handle.Isinproductframeloaded = true;
        Inproductutility.setUserLang(data.userlang);
        var stacklength = handle.apistack.length;
            if(stacklength){
        for(let iterator=0; iterator < stacklength; iterator++){
         Micssdktoserver.makecalltoframe(handle.apistack[iterator]);
        }
         handle.apistack = [];
        }
    }
        })
    }
 
    getQueryParam(list, params,isencode=true){
        let queryparam="";
        for (let i = 0; i < list.length; i++)
        {
           if(params[list[i]] == undefined || params[list[i]] == "undefined" || params[list[i]] == "null" || params[list[i]] == null || params[list[i]] === "" ) {
                           continue;
            }
            let paramvalue = isencode ? encodeURIComponent(params[list[i]]) : params[list[i]];
            queryparam+= (queryparam == "")?  ("?" + list[i] + "=" + paramvalue): ("&" + list[i] + "=" + paramvalue);
        }
        return queryparam;
    }
 
    getBodyParam(list,params){
        let bodyparam={}
        for (let i = 0; i < list.length; i++)
        {
            if(params[list[i]]) {
                    bodyparam[list[i]]=params[list[i]];
                }
            }
            return bodyparam;
        }
    }
    
    class WalkthroughAPI {
        constructor(){
            this.medium="walkthrough";
            this.apiconfig={
                "metrics":{
                    "queryparams":["promotionid","orgid","sessionstarttime","stepnumber","statuscode","errorcode","serviceid","action","walkthroughid","Scope","appID","clientportalID","orgtype"],
                    "bodyparams":[],
                    "endpoint":"/Walkthrough",
                    "requestheaders":new Map(),
                    "async":true
                    },
                "content":{
                    "queryparams":["serviceid","orgid","action","Scope","product_type","appID","clientportalID","orgtype"],
                    "bodyparams":["flowidlist"],
                    "endpoint":"/Walkthrough",
                    "requestheaders":new Map(),
                    "async":true
                    },
                "verifyflow":{
                    "queryparams":["flowidlist","status","action","serviceid","orgid"],
                    "bodyparams":[],
                    "endpoint":"/Walkthrough",
                    "requestheaders":new Map(),
                    "async":true
                },        
                "meta":{
                        
                    }
            };
        }
        sendMetric(params, httpmethod, onsuccess, onerror) {
            this.triggerAPI("metrics", httpmethod, params, onsuccess, onerror);
         }
        postVerifyStatus(params, httpmethod, onsuccess, onerror){
            this.triggerAPI("verifyflow", httpmethod, params, onsuccess, onerror);
         }
         getContent(params, httpmethod, onsuccess, onerror){
            this.triggerAPI("content", httpmethod, params, onsuccess, onerror);
        }
         getMeta(params, httpmethod, onsuccess, onerror){
            this.triggerAPI("meta", httpmethod, params, onsuccess, onerror);
         }
         triggerAPI(api_type, httpmethod, params, onsuccess, onerror){
            Micssdktoserver.callApi(this.medium, api_type, this.apiconfig[api_type].endpoint, httpmethod, this.apiconfig[api_type],this.apiconfig[api_type].requestheaders, params, onsuccess, onerror, this.apiconfig[api_type].async);
         }
    }
    
    class SelfhelpAPI{
        constructor(){
            this.medium="selfhelp";
            this.apiconfig={
                "metrics":{
                    "queryparams":["serviceid","orgid", "action", "Scope","product_type", "materialid", "materialtype", "promotionid","appID","clientportalID","orgtype"],
                    "bodyparams":[],
                    "endpoint":"/selfhelp",
                    "requestheaders":new Map(),
                    "async":true
                },
                "content":{
                },
                "meta":{
                    "queryparams":["serviceid","orgid", "action", "Scope","product_type", "searchkey", "materialidlist", "version","appID","clientportalID","orgtype", "type"],
                    "bodyparams":[],
                    "endpoint":"/selfhelp",
                    "requestheaders":new Map(),
                    "async":true
        }
            }
        }
        sendMetric(params, httpmethod, onsuccess, onerror) {
            this.triggerAPI("metrics", httpmethod, params, onsuccess, onerror);
         }
         getContent(params, httpmethod, onsuccess, onerror){
            this.triggerAPI("content", httpmethod, params, onsuccess, onerror);
        }
        postVerifyStatus(params, httpmethod, onsuccess, onerror){
            this.triggerAPI("verifyflow", httpmethod, params, onsuccess, onerror);
         }
         getMeta(params, httpmethod, onsuccess, onerror){
            this.triggerAPI("meta", httpmethod, params, onsuccess, onerror);
         }
         triggerAPI(api_type, httpmethod, params, onsuccess, onerror){
            Micssdktoserver.callApi(this.medium, api_type, this.apiconfig[api_type].endpoint, httpmethod, this.apiconfig[api_type],this.apiconfig[api_type].requestheaders, params, onsuccess, onerror, this.apiconfig[api_type].async);
         }
    }
    
    class BannerAPI{
        constructor(){
            this.medium="banner";
            this.apiconfig={
                "metrics":{
                    "queryparams":["ORGID","ServiceID","polling","frameorigin","Feedback"],
                    "bodyparams":[],
                    "endpoint":"/Notification",
                    "requestheaders":new Map(),
                    "async":true
                },
                "content":{
 
                },
                "meta":{
 
                }
            }
        }
        sendMetric(params, httpmethod, onsuccess, onerror) {
            this.triggerAPI("metrics", httpmethod, params, onsuccess, onerror);
         }
         getContent(params, httpmethod, onsuccess, onerror){
            this.triggerAPI("content", httpmethod, params, onsuccess, onerror);
        }
         getMeta(params, httpmethod, onsuccess, onerror){
            this.triggerAPI("meta", httpmethod, params, onsuccess, onerror);
         }
         triggerAPI(api_type, httpmethod, params, onsuccess, onerror){
            Micssdktoserver.callApi(this.medium, api_type, this.apiconfig[api_type].endpoint, httpmethod, this.apiconfig[api_type],this.apiconfig[api_type].requestheaders, params, onsuccess, onerror, this.apiconfig[api_type].async);
        }
    }
 
    class MessageboardAPI{
        constructor(){
            this.medium="messageboard";
            this.apiconfig={
                "metrics":{
                },
                "content":{
                    "queryparams":["serviceId","orgId","frameorigin"],
                    "bodyparams":[],
                    "endpoint":"/Stacked",
                    "requestheaders":new Map(),
                    "async":true
 
                },
                "meta":{
                    
                }
            }
        }
        sendMetric(params, httpmethod, onsuccess, onerror) {
            this.triggerAPI("metrics", httpmethod, params, onsuccess, onerror);
         }
         getContent(params, httpmethod, onsuccess, onerror){
            this.triggerAPI("content", httpmethod, params, onsuccess, onerror);
        }
         getMeta(params, httpmethod, onsuccess, onerror){
            this.triggerAPI("meta", httpmethod, params, onsuccess, onerror);
         }
         triggerAPI(api_type, httpmethod, params, onsuccess, onerror){
            Micssdktoserver.callApi(this.medium, api_type, this.apiconfig[api_type].endpoint, httpmethod, this.apiconfig[api_type],this.apiconfig[api_type].requestheaders, params, onsuccess, onerror, this.apiconfig[api_type].async);
         }
    }

class HelpRequestAPI {
    constructor() {
        this.medium = "helprequest";
        this.apiconfig = {
            "helprequest": {
               
                "queryparams": ["action", "orgid", "Scope", "pageUrl", "urlChar", "pageName", "reqId", "actionStatus", "materialType", "materialId", "time", "edited", "appID", "orgtype"],
                "bodyparams": ["description", "adminResponse"],
                "endpoint": "/userContentRequest",
                "requestheaders": new Map(),
                "async": true
            }
        };
    }

    /* ── viewUserPastRequest (client panel — "past requests") */
    fetchHelpRequests(params, onsuccess, onerror) {
        this.triggerAPI("helprequest", "post", params, onsuccess, onerror);
    }

    /* ── addUserRequest (client panel — raise new request) */
    submitHelpRequest(params, onsuccess, onerror) {
        this.triggerAPI("helprequest", "post", params, onsuccess, onerror);
    }

    /* ── updateUserRequestDetails with REOPEN (client panel — follow-up) */
    submitRemark(params, onsuccess, onerror) {
        this.triggerAPI("helprequest", "post", params, onsuccess, onerror);
    }

    triggerAPI(api_type, httpmethod, params, onsuccess, onerror) {
        Micssdktoserver.callApi(
            this.medium,
            api_type,
            this.apiconfig[api_type].endpoint,
            httpmethod,
            this.apiconfig[api_type],
            this.apiconfig[api_type].requestheaders,
            params,
            onsuccess,
            onerror,
            this.apiconfig[api_type].async
        );
    }
}
/*$Id$*/
class selfhelpsdk {
  static instance=null;
  constructor(inproduct,orgID) {
    if (selfhelpsdk.instance===null){
      selfhelpsdk.instance=this;
    }
    this.orgid=orgID;
    this.urlUtil = new PageCollection();
    this.serviceid=inproduct.serviceid;
    this.inproductconf=inproduct;
    this.micssdktoserverInstance=null;
    this.walkthroughInstance=null;
    this.customplaceholder = '';
    this.nodatahidestatus = true;
    this.indicatenodatahidestatus = false;
    this.instance=false;
    this.selftoggle = false;
    this.selfhelpmateriallist =[];
    this.searchdatalist=[];
    this.getallwalkthroughid=[];
    this.scope="Enterprise";
    this.stylereference={
      "backgroundcolor":"backgroundColor",
      "fontFamily":"fontFamily",
      "fontSize":"font-size",
      "fontWeight":"font-weight",
      "fontColor":"color",
      "boxShadow":"box-shadow",
      "borderTop":"border-top",
      "borderLeft":"border-left",
      "borderRight":"border-right",
      "borderBottom":"border-bottom",
      "height":"height",
      "width":"width",
      "iconColor":"color",
      "borderRadius":"borderRadius",
      "border":"border",
      "iconBackgroundcolor" : "backgroundColor"
    };
    this.selfhelpcontents={
       "indicatortext":"Help Hub",
       "popupheader":"Help Hub",
       "searchbarplaceholder":"Search for content",
        "emptylist":"Currently, no content is available for this page",
       "checklistEmptylist":"Currently, no checklist is available",
       "searchnotfound":"No content found",
       "tabswitch": {
          helphubdata:true,
          taskdata:true
        },
        "showindicator": true,
        "showpopupheader": true,
        floating:true
    };
    this.styleforDefaultplaceholder={
      "backgroundcolor":"#003297",
      "fontColor":"#ffff",
      "fontSize":"14px",
      "fontFamily":"inherit",
      "position":"right-top",
      "borderRadius":"",
      "width":"unset",
      "height":"unset",
      "logoSize":"20px"
    };
    this.styleforselfhelppopup={
      "home":{
        "backgroundcolor": "#ffffff",
        "fontFamily": "inherit",
        "boxShadow":"rgba(0, 0, 0, 0.1) 0px 0px 10px 1px"
      },
      "topband": {
        "backgroundcolor": "#003297",
        "fontColor": "#ffffff",
        "height":"45px",
        "fontSize": "14px",
        "fontFamily": "inherit",
        "fontWeight": "600",
        "boxShadow": "1px 0px 1px #bbc3ca",
        "borderBottom": "",
        "borderTop": "",
        "borderLeft": "",
        "borderRight": ""
      },
      "searchbar":{
        "iconColor":"#003297",
        "backgroundcolor":"white",
        "fontColor":"101010",
        "borderRadius":"4px",
        "border":"1px solid #9391917d",
        "iconSize":"17px"
      },
      "closebutton": {
        "iconColor": "#ffffff",
        "iconSize":"16px"
      },
      "noitem":{
        "fontColor": "#4b4b4b",
        "fontSize": "13px",
        "fontFamily": "inherit",
        "fontWeight": "300",
      },
      "listitem":{
        "fontColor": "#101010",
        "height":"",
        "fontSize": "12px",
        "fontFamily": "inherit",
        "fontWeight": "300",
        "backgroundcolor":"#ffffff",
        "iconColor": "#003297",
        "iconBackgroundcolor":"#0032970a",
      },
      "listitemhover":{
        "backgroundcolor":"#8989890a",
        "fontColor": "inherit"
      }
    },
    this.setSelfhelpContent=this.setStyleforSelfhelpPopup=this.setStylefordefaultPlaceholder=function(){};
    this.domainConf  = {};
    this.materialMap = {};
		this.utility = new selfhelpUtility();
    this.helphubdata = {};
    
    this.taskdata = {};
    this.urlmatcher = new UrlMatcher();
    this.taskurlmatcher = new UrlMatcher();
    this.taskbarpercentage = 0;
    this.dataversion = -1;
  }

  enablemics(){
      this.scope="Service";
  }

  initialize() {
    var handle=this;
    handle.micssdktoserverInstance=Micssdktoserver.getinstance(this.inproductconf,this.orgid,"selfhelp");
    if (sessionStorage.getItem("selfhelpverifydata")) {
        handle.setverifydata(sessionStorage.getItem("selfhelpverifydata"));
        sessionStorage.removeItem("selfhelpverifydata");
    }
    if(!handle.verification){
        handle.getdatacallback(handle,"Enterprise");
        if(handle.scope===!"Enterprise"){ //now only get meta for micse
              handle.getdatacallback(handle,"Service")
        }
    }
    handle.walkthroughInstance = WalkthroughSDK.getInstance();
    handle.instance=true;
    const bodyelem = document.body;
  bodyelem.insertAdjacentHTML(
  `beforeend`,
  `
    ${this.customplaceholder ? `` : `
      <div id="selfhelpicon" class="${this.styleforDefaultplaceholder.position}">
        <div id="micsselfhelptoggler" style="background-color:${this.styleforDefaultplaceholder.backgroundcolor}">
          <svg width="20px" height="20px" id="helphublogoinwidget" viewBox="0 0 281 246" fill="${this.styleforDefaultplaceholder.fontColor}">
            <path fill-rule="evenodd" clip-rule="evenodd" d="M0 21C0 9.40201 9.40202 0 21 0H259.538C271.136 0 280.538 9.40202 280.538 21V192.992C280.538 204.59 271.136 213.992 259.538 213.992H21C9.40204 213.992 0 204.59 0 192.992V21ZM134.397 91.334C134.397 101.063 129.14 108.949 122.654 108.949C116.168 108.949 110.91 101.063 110.91 91.334C110.91 81.6053 116.168 73.7188 122.654 73.7188C129.14 73.7188 134.397 81.6053 134.397 91.334ZM170.281 108.949C176.766 108.949 182.024 101.063 182.024 91.334C182.024 81.6053 176.766 73.7188 170.281 73.7188C163.795 73.7188 158.537 81.6053 158.537 91.334C158.537 101.063 163.795 108.949 170.281 108.949Z" fill=""/>
            <path d="M143.012 242.675C141.813 244.305 139.377 244.305 138.178 242.675L113.881 209.636C112.424 207.655 113.838 204.859 116.298 204.859H164.893C167.352 204.859 168.767 207.655 167.31 209.636L143.012 242.675Z" fill=""/>
          </svg>
          ${this.renderindicator()}
            ${this.renderDrag()}
        </div>
      </div>
    `}

    <div id="micsselfhelpContainer" class="${this.styleforDefaultplaceholder.position}" style="background:${this.styleforselfhelppopup.listitem.backgroundcolor}">
      
      <div id="topbar" style="background-color:${this.styleforselfhelppopup.topband.backgroundcolor};color:${this.styleforselfhelppopup.topband.fontColor}">
        <div id="helphublogotextcontainer">
          <svg width="22px" height="22px" viewBox="0 0 281 246" fill="${this.styleforselfhelppopup.topband.fontColor}">
            <path fill-rule="evenodd" clip-rule="evenodd" d="M0 21C0 9.40201 9.40202 0 21 0H259.538C271.136 0 280.538 9.40202 280.538 21V192.992C280.538 204.59 271.136 213.992 259.538 213.992H21C9.40204 213.992 0 204.59 0 192.992V21ZM134.397 91.334C134.397 101.063 129.14 108.949 122.654 108.949C116.168 108.949 110.91 101.063 110.91 91.334C110.91 81.6053 116.168 73.7188 122.654 73.7188C129.14 73.7188 134.397 81.6053 134.397 91.334ZM170.281 108.949C176.766 108.949 182.024 101.063 182.024 91.334C182.024 81.6053 176.766 73.7188 170.281 73.7188C163.795 73.7188 158.537 81.6053 158.537 91.334C158.537 101.063 163.795 108.949 170.281 108.949Z" fill=""/>
            <path d="M143.012 242.675C141.813 244.305 139.377 244.305 138.178 242.675L113.881 209.636C112.424 207.655 113.838 204.859 116.298 204.859H164.893C167.352 204.859 168.767 207.655 167.31 209.636L143.012 242.675Z" fill=""/>
          </svg>
          ${this.renderpopupheader()}
        </div>
      
        <svg id="micsselfhelpclosableIcon" viewBox="-3 -3 30 30" width="20" height="20" fill="none" stroke="${this.styleforselfhelppopup.topband.fontColor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M18 6L6 18M6 6l12 12"></path>
        </svg>
      </div>

      ${this.renderTabSwitch()}
      ${this.renderTaskbar()}

      <div id="materiallistsearchbar">
        <svg id="searchicon" fill="none" stroke="${this.styleforselfhelppopup.topband.fontColor}" viewBox="0 0 16 16">
          <path d="m14.48,12.18l-3.61-3.61s-.03-.02-.05-.03c.36-.71.58-1.49.58-2.34,0-2.87-2.33-5.2-5.2-5.2S1,3.33,1,6.2s2.33,5.2,5.2,5.2c.85,0,1.63-.22,2.34-.58.01.02.02.03.03.05l3.61,3.61c.32.32.73.47,1.15.47s.83-.16,1.15-.47c.63-.63.63-1.66,0-2.3ZM2,6.2c0-2.32,1.88-4.2,4.2-4.2s4.2,1.88,4.2,4.2-1.88,4.2-4.2,4.2-4.2-1.88-4.2-4.2Zm11.77,7.57c-.24.24-.64.24-.88,0l-3.49-3.5c.33-.26.62-.55.88-.88l3.5,3.49c.24.24.24.64,0,.88Z"></path>
        </svg>
        <input type="text" id="micsselfhelpsearchinput" autocomplete="off" autocorrect="off" autocapitalize="off" placeholder="${this.selfhelpcontents.searchbarplaceholder}">
      </div>

      <div id="materiallistcontainer"></div>
    </div>
  `
);


    document.getElementById('micsselfhelptoggler').addEventListener('click', this.showselfhelpPopup.bind(this));
    this.applyplaceholderstyles();
    document.getElementById('micsselfhelpclosableIcon').addEventListener('click', this.showselfhelpPopup.bind(this));
    document.getElementById('micsselfhelpsearchinput').addEventListener('keyup', function() {
    handle.materialsearch(handle);
        });
    this.togglediv=document.getElementById('micsselfhelpContainer');
    this.urlchangeListner();
    this.tabswitch(this.selectedtab);
    this.selfhelpcontents.floating ? this.enableDrag("selfhelpicon","micsselfhelpContainer") : '';
    this.initTabListeners();
    this.addListInMaterial();
  }
  enableDrag(draggableId, containerId) {
  const draggable = document.getElementById(draggableId);
    const container = document.getElementById(containerId);
  if (!draggable) return;
  let pointerStartX = 0, pointerStartY = 0; let elementStartLeft = 0, elementStartTop = 0; let dragOffsetX = 0, dragOffsetY = 0; let isDragging = false, hasPointerCapture = false;

  const SNAP_CLASSES = [ "top-left","top-center","top-right", "bottom-left","bottom-center","bottom-right", "left-top","left-center","left-bottom", "right-top","right-center","right-bottom" ];

  const removeSnapClasses = el =>
    SNAP_CLASSES.forEach(cls => el.classList.remove(cls));

  const isDragHandle = target => target.closest?.(".drag-handle");

  draggable.onpointerdown = e => {
    if (!isDragHandle(e.target)) return;

      isDragging = true;
    try { draggable.setPointerCapture(e.pointerId); hasPointerCapture = true; } catch {}

    const rect = draggable.getBoundingClientRect();
    elementStartLeft = rect.left;
    elementStartTop = rect.top;
    pointerStartX = e.clientX;
    pointerStartY = e.clientY;

    Object.assign(draggable.style, {
      position: "fixed",
      left: elementStartLeft + "px",
      top: elementStartTop + "px",
      right: "auto",
      bottom: "auto",
      transform: "none"
      });
      e.preventDefault();
  };

  draggable.onpointermove = e => {
      if (!isDragging) return;
    dragOffsetX = e.clientX - pointerStartX;
    dragOffsetY = e.clientY - pointerStartY;
    draggable.style.transform = `translate(${dragOffsetX}px, ${dragOffsetY}px)`;
  };

  draggable.onpointerup = draggable.onpointercancel = e => {
      if (!isDragging) return;
      isDragging = false;
    try { hasPointerCapture && draggable.releasePointerCapture(e.pointerId); } catch {}
    draggable.style.transform = "none";
    const viewportWidth = innerWidth;
    const viewportHeight = innerHeight;
    const elementWidth = draggable.offsetWidth;
    const elementHeight = draggable.offsetHeight;

    let finalLeft = Math.min(
      Math.max(elementStartLeft + dragOffsetX, 0),
      viewportWidth - elementWidth
    );
    let finalTop = Math.min(
      Math.max(elementStartTop + dragOffsetY, 0),
      viewportHeight - elementHeight
    );

    Object.assign(draggable.style, {
      left: finalLeft + "px",
      top: finalTop + "px"
    });

    let rect = draggable.getBoundingClientRect();

    const distancesToEdges = {
        left: rect.left,
      right: viewportWidth - rect.right,
        top: rect.top,
      bottom: viewportHeight - rect.bottom
      };

    const nearestSide = Object.entries(distancesToEdges)
      .sort((a, b) => a[1] - b[1])[0][0];

    const segment = (nearestSide === "top" || nearestSide === "bottom") ? rect.left < viewportWidth / 3 ? "left"  : rect.right > viewportWidth * 2 / 3  ? "right" : "center"  : rect.top < viewportHeight / 3  ? "top" : rect.bottom > viewportHeight * 2 / 3 ? "bottom" : "center";
    if (nearestSide === "left") draggable.style.left = "0px";
    else if (nearestSide === "right") draggable.style.left = "auto", draggable.style.right = "0px";
    else if (nearestSide === "top") draggable.style.top = "0px";
    else draggable.style.top = "auto", draggable.style.bottom = "0px";

    const CORNER_PADDING = 120;
    rect = draggable.getBoundingClientRect();
    if (nearestSide === "top" || nearestSide === "bottom") {
      if (rect.left < CORNER_PADDING)
        draggable.style.left = CORNER_PADDING + "px";
      else if (rect.right > viewportWidth - CORNER_PADDING)
        draggable.style.left = viewportWidth - rect.width - CORNER_PADDING + "px";
    } else {
      if (rect.top < CORNER_PADDING)
        draggable.style.top = CORNER_PADDING + "px";
      else if (rect.bottom > viewportHeight - CORNER_PADDING)
        draggable.style.top = viewportHeight - rect.height - CORNER_PADDING + "px";
    }
    removeSnapClasses(draggable);
    removeSnapClasses(container);
      const snapClass = `${nearestSide}-${segment}`;
    draggable.classList.add(snapClass);
      container.classList.add(snapClass);
    dragOffsetX = dragOffsetY = 0;
  };
  }






  tabswitch(activeTabId) {
    var handle = this;
    var container = document.querySelector('#micsselfhelpContainer');
    var tabs = container?.querySelectorAll('#tabswitch #left #tabs .tab') || [];
    var activeTab = container?.querySelector(`#tabswitch #left #tabs #${activeTabId}`) || null;
    var search = container?.querySelector('#materiallistsearchbar') || null;
    var task = container?.querySelector('#taskbar') || null;

    tabs.forEach(t => t.classList.remove("selected"));
    if (activeTab) activeTab.classList.add("selected");

    if (activeTabId === "helphubdata") {
      if (search) search.style.display = "flex";
      if (task) task.style.display = "none";
    }
    else {
      if (search) search.style.display = "none";
      if (task) task.style.display = "flex";
    }
    var searchInput = container?.querySelector('#micsselfhelpsearchinput');
    if (searchInput && searchInput.value !== '') {
      searchInput.value = '';
    }
  }
  initTabListeners() {
    var handle = this;
    var tabs = document.querySelectorAll('#micsselfhelpContainer #tabswitch #left #tabs .tab');
    tabs.forEach(tab => {
      tab.addEventListener("click", () => {
        handle.selectedtab = tab.id;
        handle.tabswitch(tab.id);
        handle.addListInMaterial();
      }, { once: false });
    });
  }
  renderTabSwitch() {
    const tabs = {
      helphubdata: {
        label: "Help",
        svg: `
          <svg viewBox="0 -960 960 960">
            <path d="M478-240q21 0 35.5-14.5T528-290q0-21-14.5-35.5T478-340q-21 0-35.5 14.5T428-290q0 21 14.5 35.5T478-240Zm-36-154h74q0-33 7.5-52t42.5-52q26-26 41-49.5t15-56.5q0-56-41-86t-97-30q-57 0-92.5 30T342-618l66 26q5-18 22.5-39t53.5-21q32 0 48 17.5t16 38.5q0 20-12 37.5T506-526q-44 39-54 59t-10 73Zm38 314q-83 0-156-31.5T197-197q-54-54-85.5-127T80-480q0-83 31.5-156T197-763q54-54 127-85.5T480-880q83 0 156 31.5T763-763q54 54 85.5 127T880-480q0 83-31.5 156T763-197q-54 54-127 85.5T480-80Zm0-80Z"></path>
          </svg>`
      },
      taskdata: {
        label: "Checklist",
        svg: `
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M3 5H9V11H3V5ZM5 7V9H7V7H5ZM11 7H21V9H11V7ZM11 15H21V17H11V15ZM5 20L1.5 16.5L2.91 15.09L5 17.17L9.59 12.59L11 14L5 20Z" fill="black"></path>
          </svg>`
      }
    };
    var enabledTabs = Object.keys(this.selfhelpcontents.tabswitch).filter(k => this.selfhelpcontents.tabswitch[k]);
    this.selectedtab = this.selectedtab || (enabledTabs[0] || null);
    if (enabledTabs.length <= 1) return "";
    const htmlTabs = enabledTabs.map(key => `
      <div class="tab ${key === this.selectedtab ? 'selected' : ''}" id="${key}">
        ${tabs[key].svg}
        ${tabs[key].label}
      </div>
    `).join("");
    return `
      <div id="tabswitch">
        <div id="left">
          <div id="tabs">
            ${htmlTabs}
          </div>
        </div>
      </div>
    `;
  }
  renderTaskbar(){
    return `        <div id="taskbar">
                        <div id="zohodaptop">
                          <div id="heading">Your Progress</div>
                          <div id="per">${this.taskbarpercentage}%</div>
                        </div>
                        <div id="barcontainer">
                          <div id="bar">
                            <div id="completed" style="width: ${this.taskbarpercentage}%;"></div>
                          </div>
                      </div>
                    </div>`
  }
  renderDrag(){
    return this.selfhelpcontents.floating ?  `<div class="drag-handle">
              <svg height="24px" viewBox="0 -960 960 960" width="24px" fill="#FFFFFF"><path d="M360-160q-33 0-56.5-23.5T280-240q0-33 23.5-56.5T360-320q33 0 56.5 23.5T440-240q0 33-23.5 56.5T360-160Zm240 0q-33 0-56.5-23.5T520-240q0-33 23.5-56.5T600-320q33 0 56.5 23.5T680-240q0 33-23.5 56.5T600-160ZM360-400q-33 0-56.5-23.5T280-480q0-33 23.5-56.5T360-560q33 0 56.5 23.5T440-480q0 33-23.5 56.5T360-400Zm240 0q-33 0-56.5-23.5T520-480q0-33 23.5-56.5T600-560q33 0 56.5 23.5T680-480q0 33-23.5 56.5T600-400ZM360-640q-33 0-56.5-23.5T280-720q0-33 23.5-56.5T360-800q33 0 56.5 23.5T440-720q0 33-23.5 56.5T360-640Zm240 0q-33 0-56.5-23.5T520-720q0-33 23.5-56.5T600-800q33 0 56.5 23.5T680-720q0 33-23.5 56.5T600-640Z"/></svg>
            </div>` : ``;
  }
  renderindicator(){
        return this.selfhelpcontents.showindicator ?  `<span id="textself" style="color:${this.styleforDefaultplaceholder.fontColor}">${this.selfhelpcontents.indicatortext}</span>` : ``;
  }
  renderpopupheader(){
            return this.selfhelpcontents.showpopupheader ?  `<span id="text">${this.selfhelpcontents.popupheader}</span>` : ``;
  }
      findMaterialIndex(material) {
        for (const path in this.taskdata) {
          const index = this.taskdata[path].findIndex(
            item =>
              item.materialid === material.id &&
              item.workspaceid === material.workspaceid
          );

          if (index !== -1) {
            return { path, index, item: this.taskdata[path][index] };
          }
        }
        return null;
    }
calculateTaskBarPercentage() {
  var items = [];
  if (this.dataversion === 1) {
    this.selfhelpmateriallist.forEach(list => {
      list.panellist.forEach(panel => {
        items = [...items, ...panel.materiallist];
      });
    });
  } else {
    items = Object.values(this.taskdata).flat();
  }
  var uniqueItemsMap = new Map();
  items.forEach(item => {
    var id = item.materialid || item.id;
    if (id) {
      if (!uniqueItemsMap.has(id) || item.status === 'completed') {
        uniqueItemsMap.set(id, item);
      }
    }
  });
  items = Array.from(uniqueItemsMap.values());

  var completed = items.filter(material => material.status == "completed").length;
  var total = items.length;
  var percentage = total ? Math.round((completed / total) * 100) : 0;
  this.taskbarpercentage = percentage;
  var taskbar = document.querySelector("#micsselfhelpContainer #taskbar");
  if (taskbar) {
      var perElement = taskbar.querySelector("#per");
      var completedElement = taskbar.querySelector("#completed");
      if (perElement) perElement.textContent = percentage + "%";
      if (completedElement) completedElement.style.width = percentage + "%";
  }
  return percentage;
}


  setStyleforHelphubPlaceholder(stylefordefaultplaceholder={}){
      this.styleforDefaultplaceholder=this.updatedefaultjson(this.styleforDefaultplaceholder,stylefordefaultplaceholder);
      if(this.instance){
        this.applyplaceholderstyles();
      }  
  }
  setStyleforHelphubPopup(styleforselfhelppopup={}){
    this.styleforselfhelppopup=this.updatedefaultjson(this.styleforselfhelppopup,styleforselfhelppopup);
    if(this.instance){
    this.applypopupstyles();
    }
  }
  setHelphubContent(selfhelpcontents={}){
    this.selfhelpcontents=this.updatedefaultjson(this.selfhelpcontents,selfhelpcontents);
  }
  
  changeHelphubPlaceholder(indicatorID){
    var handle=this;
    handle.customplaceholder= document.getElementById(indicatorID);
    handle.customplaceholder?handle.customplaceholder.addEventListener('click',function(){
        handle.showselfhelpPopup();
    }):'';
  }
  updateStyleConfig(newValues) {
    var deepMerge = (target, source) => {
      for (var key in source) {
        var incomingValue = source[key];
        var isObject = incomingValue && typeof incomingValue === "object" && !Array.isArray(incomingValue);
        if (isObject) {
          target[key] = deepMerge(target[key] || {}, incomingValue);
        } 
        else {
          target[key] = incomingValue;
        }
      }
      return target;
    };
    for (var mainKey in newValues) {
      if (this[mainKey]) {
        deepMerge(this[mainKey], newValues[mainKey]);
      }
    }
  }
  onContentClose(type, materialID) {
    var handle = this;
    var completedItem = null;

    for (const path in this.taskdata) {
      const index = this.taskdata[path].findIndex(
        item =>
          String(item.materialid) === String(materialID) &&
          item.materialtype.toLowerCase() === type.toLowerCase()
      );
      if (index !== -1) {
        completedItem = this.taskdata[path][index];
        break;
      }
    }

    if (!completedItem && handle.verification) {
      for (const list of handle.selfhelpmateriallist) {
        for (const panel of list.panellist) {
          completedItem = panel.materiallist.find(
            item => String(item.id) === String(materialID) && item.type.toLowerCase() === type.toLowerCase()
          );
          if (completedItem) break;
        }
        if (completedItem) break;
      }
    }

    if (!completedItem) {
      return;
    }

    if (handle.verification) {
      completedItem.status = "completed";
      handle.calculateTaskBarPercentage();
      handle.addListInMaterial();
    } else {
      handle.getdatacallback(handle, handle.scope, "checklist");
    }
  }

  getdatacallback( handle , scope , type){
    this.setData(handle ,scope , type);
  }

  setverifydata(message){
    this.verification = true;
    this.verificationcontent = message;
    var messageContent = typeof message === "string" ? JSON.parse(message) : message;
    var type = messageContent.type;
    if (messageContent.message) {
      messageContent = messageContent.message;
    }
    
    this.dataversion = 2;
    let dataObj = {};
    if(messageContent.helphubList && messageContent.helphubList[0]){
        let dataList = messageContent.helphubList[0];
        dataObj[dataList.url] ? "" : dataObj[dataList.url] = [];
        for (var selfhelpmaterialList of dataList.panellist){
            for(var materialItem of selfhelpmaterialList.materiallist){
                var materialData = {
                    scope: selfhelpmaterialList.Scope,
                    promotionid: selfhelpmaterialList.id,
                    materialid: materialItem.id,
                    materialtype: materialItem.type,
                    displayname: materialItem.displayname,
                    workspaceid: materialItem.workspaceid 
                }
                dataObj[dataList.url].push(materialData);
            }  
        }
    }
    
    this.selfhelpcontents.tabswitch = { helphubdata: true, taskdata: true };
    if (type === 'checklist') {
        this.taskdata = {...this.taskdata, ...dataObj};
        this.inserttaskurlsformatch(Object.keys(this.taskdata));
        this.selectedtab = 'taskdata';
        this.calculateTaskBarPercentage();
    } else {
        this.helphubdata = {...this.helphubdata, ...dataObj};
        this.inserturlsformatch(Object.keys(this.helphubdata));
        this.selectedtab = 'helphubdata';
    }

    if (this.instance) {
      this.addListInMaterial();
      if (!this.selftoggle) {
        this.showselfhelpPopup();
      }
    }
  }

  orgerror(xhttp){ 
    var handle = selfhelpsdk.instance || this;
    setTimeout(function(){ handle.initialize() },30000);
    return false;
  }

  setData(handle, scope , type) {
    var params = {
        "orgid":handle.orgid,
        "serviceid":handle.serviceid,
        "action":"getTip",
        "Scope":scope,
        "version": 2,
    };
    type ? params.type = type : "";
    handle.micssdktoserverInstance.getMeta(params,"get",
    function orgsuccess(parsingmeta){
       try{
        if (!parsingmeta) {
            return;
        }
        parsingmeta = JSON.parse(parsingmeta);
        handle.dataversion = parsingmeta.version;

        switch (handle.dataversion) {
            case 1:
                handle.nodatahidestatus = parsingmeta.nodatahidestatus;
                parsingmeta = parsingmeta.hubdata;
                handle.selfhelpmateriallist = [...handle.selfhelpmateriallist, ...parsingmeta];
                break;

            case 2:
                handle.nodatahidestatus = parsingmeta.nodatahidestatus;
                // helphubdata — only for Help Hub tab
                if(parsingmeta.hubdata){
                    handle.helphubdata = parsingmeta.hubdata;
                    handle.inserturlsformatch(Object.keys(handle.helphubdata));
                }
                // taskdata — only for Tasks tab
                if(parsingmeta.checklist){
                    handle.taskdata = parsingmeta.checklist;
                    handle.inserttaskurlsformatch(Object.keys(handle.taskdata));
                    // calculate percentage from taskdata and update taskbar in-place
                    handle.calculateTaskBarPercentage();
                }
                break;
              }
          }catch(error){
            handle.orgerror(error);
          }
        handle.addListInMaterial();

    },handle.orgerror);
  }

  inserturlsformatch(urls){
    for(let i=0; i<urls.length; i++){
      this.urlmatcher.insert(urls[i]);
    }
  }
  inserttaskurlsformatch(urls){
    for(let i=0; i<urls.length; i++){
      this.taskurlmatcher.insert(urls[i]);
    }
  }
  
  selfhelpurlmatch(url, pattern) { //Pattern matching algorithm
    return this.urlUtil.doesUrlEndsWith_WildcardPatternMatch(url, pattern);
  }

  urlchangeListner() {
        var handle = this;
        var originalPushState = history.pushState;
        var originalReplaceState = history.replaceState;
    
        history.pushState = function() {
            originalPushState.apply(history, arguments);
            handle.hideselfhelpforurlchange(handle);
        };
    
        history.replaceState = function() {
            originalReplaceState.apply(history, arguments);
            handle.hideselfhelpforurlchange(handle);
        };
    
        window.addEventListener('popstate', function(event) {
            handle.hideselfhelpforurlchange(handle);
        });
    
        window.addEventListener('hashchange', function() {
            handle.hideselfhelpforurlchange(handle);
        });
    }
    
  hideselfhelpforurlchange(handle){
    handle.addListInMaterial();
    if(!handle.selftoggle){
    return;
    }
    handle.showselfhelpPopup();
    }
  
  showselfhelpPopup() {
    this.selftoggle = !this.selftoggle;
    var setsearchempty = document.getElementById('micsselfhelpsearchinput').value;
    setsearchempty ? document.getElementById('micsselfhelpsearchinput').value='' : '';
    this.createmateriallist();
  }
 
  createmateriallist(){
    if (this.selftoggle) {
        this.addListInMaterial(); 
        this.applyplaceholderstyles();
        this.showMaterialContainerWithEffect();
        if(!this.customplaceholder){
          this.hideSelfhelpButtonwithEffect();
        }
        //metric collection selfhelp click("medium")
        return '';
    }
    this.hideMaterialContainerWithEffect();
    if(!this.customplaceholder && this.indicatenodatahidestatus){
      this.showSelfhelpButtonwithEffect();
    }
  } 
 
  addListInMaterial() {
      var handle=this;
      var materiallistid = document.getElementById('materiallistcontainer');
      var emptyMessage = handle.selectedtab === 'taskdata' ? handle.selfhelpcontents.checklistEmptylist : handle.selfhelpcontents.emptylist;
      materiallistid.innerHTML = ('<span style="margin:auto;text-align:center;font-size:' + handle.styleforselfhelppopup.noitem.fontSize + ';font-family:' + handle.styleforselfhelppopup.noitem.fontFamily + ';font-weight:' + handle.styleforselfhelppopup.noitem.fontWeight + ';color:' + handle.styleforselfhelppopup.noitem.fontColor + '">' + emptyMessage + '</span>');
      var currenturl=location.href.replace(location.origin,"");
      handle.searchdatalist=[];
      handle.getallwalkthroughid={"Enterprise":[],"Service":[]};
			
      this.materialMap = {};
      for (var item of this.selfhelpmateriallist) {
        handle.searchdatalist =  this.selfhelpurlmatch(currenturl, item.url) ? [...item.panellist, ...handle.searchdatalist] :  [...handle.searchdatalist, ...item.panellist];   // Matches add to the beginning & Not matches add to the end
      }
      // if need filter the dublicate walkthrough id's here.
      if(handle.searchdatalist.length){
        materiallistid.innerHTML='';
      }
      let fragment = '';
      switch(handle.dataversion){
        case 1:
          fragment = handle.renderdataversion1(handle);
          break;
        case 2:
          fragment = handle.renderdataversion2(currenturl, handle);
          break;
        default:
          fragment = handle.renderdataversion1(handle);
          break;
      }

      var hasContent = fragment.childNodes.length > 0;
      var hasAnyContent = hasContent;

      if (handle.dataversion === 2) {
        var helphubHasData = false;
        if (handle.helphubdata) {
          for (var key in handle.helphubdata) {
            if (handle.helphubdata[key] && handle.helphubdata[key].length > 0) {
              helphubHasData = true; break;
            }
          }
        }
        var taskHasData = false;
        if (handle.taskdata) {
          for (var key in handle.taskdata) {
            if (handle.taskdata[key] && handle.taskdata[key].length > 0) {
              taskHasData = true; break;
            }
          }
        }
        hasAnyContent = helphubHasData || taskHasData;
      }

      if(hasContent){
      handle.indicatenodatahidestatus = true;
      materiallistid.innerHTML='';
      materiallistid.appendChild(fragment);
      }  

      if (hasAnyContent) {
        handle.indicatenodatahidestatus = true;
      }

      if(!hasAnyContent && handle.nodatahidestatus){
        handle.indicatenodatahidestatus = false;
        handle.hideSelfhelpButtonwithEffect();
      }

      else if (!handle.selftoggle && ((hasAnyContent && handle.nodatahidestatus) || !handle.nodatahidestatus)) {
        handle.indicatenodatahidestatus = true;
        handle.showSelfhelpButtonwithEffect();
      }
      
      else if(!handle.selftoggle && !handle.nodatahidestatus){
        handle.showSelfhelpButtonwithEffect();
      }

      var taskbar = document.querySelector("#micsselfhelpContainer #taskbar");
      if (taskbar && handle.selectedtab === 'taskdata') {
        taskbar.style.display = hasContent ? "flex" : "none";
      }

      this.loadWalkthroughs(handle.getallwalkthroughid);

      if (handle.dataversion === 2) {
        var selecteddata = handle.selectedtab === 'taskdata'
          ? handle.helphubdata
          : handle.taskdata;

        if (selecteddata) {
          var selectedWalkthroughIds = { "Enterprise": [], "Service": [] };
          for (var url in selecteddata) {
            for (var item of selecteddata[url]) {
              if (item.materialtype === 'walkthrough') {
                var itemScope = item.scope || handle.scope || "Enterprise";
                selectedWalkthroughIds[itemScope] = selectedWalkthroughIds[itemScope] || [];
                if (!selectedWalkthroughIds[itemScope].includes(item.materialid)) {
                  selectedWalkthroughIds[itemScope].push(item.materialid);
                }
              }
            }
          }
          this.loadWalkthroughs(selectedWalkthroughIds);
        }
      }
      handle.setdynamicstyleforlist();
    }

    renderdataversion1(handle){
      let fragment = document.createDocumentFragment();
      for (var selfhelpmaterialList of handle.searchdatalist){
        for(var materialItem of selfhelpmaterialList.materiallist){
          if(this.materialMap[materialItem.id] !== undefined){
              continue;
          }
          var displayData = handle.getMaterialIconByType(materialItem.type);

					var materialData = {
            scope: selfhelpmaterialList.Scope,
            panelId: selfhelpmaterialList.id,
            id: materialItem.id,
            type: materialItem.type,
            displayname: materialItem.displayname,
            displayData: displayData,
            workspaceid: materialItem.workspaceid
          }

          this.materialMap[materialItem.id] = materialData;

					let flowDiv = handle.utility.createFlowlist(document, materialData, handle);
					fragment.appendChild(flowDiv);

          if(materialItem.type == 'walkthrough'){
            handle.getallwalkthroughid[selfhelpmaterialList.Scope].push(materialItem.id);             
          }
        }
      }
      return fragment;
    }

    renderdataversion2(currenturl, handle){

      let fragment = document.createDocumentFragment();

      // guard against null selectedtab (single-tab config)
      if (!handle.selectedtab) {
        return fragment;
      }

      var urlmatches = handle.selectedtab === 'taskdata'
        ? handle.taskurlmatcher.search(currenturl)
        : handle.urlmatcher.search(currenturl);

      var materiallist = [];
      var finaldata = handle[handle.selectedtab];

      if (!finaldata) {
        return fragment;
      }

      var availableurls = Object.keys(finaldata);
      for(let i=0; i<availableurls.length; i++){
        if(urlmatches.includes(availableurls[i])){
          materiallist = [...finaldata[availableurls[i]], ...materiallist];
        }
        else{
          materiallist = [...materiallist, ...finaldata[availableurls[i]]];
        }
      }
      for(var materialItem of materiallist){
        if(handle.materialMap[materialItem.materialid] !== undefined){
          continue;
        }
        var displayData = handle.getMaterialIconByType(materialItem.materialtype);
  
        var materialData = {
          scope: materialItem.scope,
          panelId: materialItem.promotionid !== undefined ? materialItem.promotionid : materialItem.panelid,
          id: materialItem.materialid,
          type: materialItem.materialtype,
          displayname: materialItem.displayname,
          displayData: displayData,
          workspaceid: materialItem.workspaceid,
          status: materialItem.status ? materialItem.status : 'not completed'
        };
  
        handle.materialMap[materialItem.materialid] = materialData;
  
        let flowDiv = handle.utility.createFlowlist(document, materialData, handle);
        fragment.appendChild(flowDiv);
  
        if(materialItem.materialtype == 'walkthrough'){
          handle.getallwalkthroughid[materialItem.scope].push(materialItem.materialid);             
        }
      }
      return fragment;
    }


    loadWalkthroughs(data){
      this.walkthroughInstance.loadFlow(data["Service"],"Service");
      this.walkthroughInstance.loadFlow(data["Enterprise"],"Enterprise");
    }
    getMaterialIconByType(type) {
      switch (type.toLowerCase()) {
        case "walkthrough":
          return {icon:`<svg viewBox="0 0 32 32" class="materialdesign"><path class="" d="M5.5.6C2.8.6.6,2.8.6,5.5s2.2,4.9,4.9,4.9,4.9-2.2,4.9-4.9S8.2.6,5.5.6ZM5.5,8.6c-1.7,0-3.1-1.4-3.1-3.1s1.4-3.1,3.1-3.1,3.1,1.4,3.1,3.1-1.4,3.1-3.1,3.1Z" stroke-width="0"></path><path class="" d="M15.9,11.3c-2.7,0-4.9,2.2-4.9,4.9s2.2,4.9,4.9,4.9,4.9-2.2,4.9-4.9-2.2-4.9-4.9-4.9ZM15.9,19.3c-1.7,0-3.1-1.4-3.1-3.1s1.4-3.1,3.1-3.1,3.1,1.4,3.1,3.1-1.4,3.1-3.1,3.1Z" stroke-width="0"></path><path class="" d="M26.2,21.6c-2.7,0-4.9,2.2-4.9,4.9s2.2,4.9,4.9,4.9,4.9-2.2,4.9-4.9-2.2-4.9-4.9-4.9ZM26.2,29.6c-1.7,0-3.1-1.4-3.1-3.1s1.4-3.1,3.1-3.1,3.1,1.4,3.1,3.1-1.4,3.1-3.1,3.1Z" stroke-width="0"></path><g><path class="" d="M6.5,21.6h0c0-2.4,2-4.4,4.4-4.4h1.1v-1.9h-1.1c-3.5,0-6.3,2.8-6.3,6.3h0c0,3.5,2.8,6.3,6.3,6.3h11.6v-1.9h-11.6c-2.4,0-4.4-2-4.4-4.4Z" stroke-width="0"></path><path class="" d="M21,4.5h-11.5v1.9h11.5c2.4,0,4.4,2,4.4,4.4h0c0,2.4-2,4.4-4.4,4.4h-1.3v1.9h1.3c3.5,0,6.3-2.8,6.3-6.3h0c0-3.5-2.8-6.3-6.3-6.3Z" stroke-width="0"></path></g></svg>`,
                  displaytype : 'Walkthrough'};
        case "interactivevideo":
          return {icon:`<svg viewBox="0 0 122 118" fill="none" class="materialdesign"><path d="M5 76.4456V17C5 10.3726 10.3726 5 17 5H105C111.627 5 117 10.3726 117 17V76.4456C117 83.073 111.627 88.4456 105 88.4456H75.7959C73.7177 88.4456 71.721 89.2543 70.2286 90.7006L48.1613 112.085C47.4905 112.735 46.3738 112.192 46.4708 111.263L47.9304 97.2759C48.423 92.5548 44.7203 88.4456 39.9736 88.4456H17C10.3726 88.4456 5 83.073 5 76.4456Z" fill="none" stroke-width="8"></path><path fill="none" d="M48 62.6646V32.3034C48 30.8006 49.5954 29.8346 50.9271 30.5312L79.6472 45.5553C81.0709 46.3001 81.0796 48.3348 79.6622 49.0917L50.9421 64.4288C49.6099 65.1403 48 64.175 48 62.6646Z" stroke-width="8"></path></svg>`,
                  displaytype : 'Interactive Video'};
        case "guide":
          return  {icon:`<svg viewBox="0 0 16 16" class="materialdesign"><defs><style>.cls-1{stroke-width:0px;}</style></defs><path class="cls-1" d="m13.73,5.56l-3.81-4.02c-.33-.35-.79-.54-1.26-.54H3.22c-.79,0-1.43.64-1.43,1.43v11.14c0,.79.64,1.43,1.43,1.43h9.55c.79,0,1.43-.64,1.43-1.43v-6.81c0-.45-.17-.87-.48-1.2Zm-.94.46l-3-.11c-.24,0-.43-.19-.43-.45l-.11-3.18,3.54,3.74Zm-.01,7.98H3.22c-.24,0-.43-.19-.43-.43V2.43c0-.24.19-.43.43-.43h5.01l.12,3.48c0,.79.64,1.43,1.41,1.43h0l3.29.12s.01,0,.02,0c.05,0,.09-.01.13-.03v6.56c0,.24-.19.43-.43.43Z"/><path class="cls-1" d="m10.54,8.46h-4.88c-.28,0-.5.22-.5.5s.22.5.5.5h4.88c.28,0,.5-.22.5-.5s-.22-.5-.5-.5Z"/><path class="cls-1" d="m10.54,10.74h-4.88c-.28,0-.5.22-.5.5s.22.5.5.5h4.88c.28,0,.5-.22.5-.5s-.22-.5-.5-.5Z"/></svg>`,
                  displaytype : 'Guide'};
        case "externalcontent":
          return {icon:`<svg viewBox="0 0 16 16" class="materialdesign"><defs><style>.cls-1{stroke-width:0px;}</style></defs><path class="cls-1" d="m13.73,5.56l-3.81-4.02c-.33-.35-.79-.54-1.26-.54H3.22c-.79,0-1.43.64-1.43,1.43v11.14c0,.79.64,1.43,1.43,1.43h9.55c.79,0,1.43-.64,1.43-1.43v-6.81c0-.45-.17-.87-.48-1.2Zm-.94.46l-3-.11c-.24,0-.43-.19-.43-.45l-.11-3.18,3.54,3.74Zm-.01,7.98H3.22c-.24,0-.43-.19-.43-.43V2.43c0-.24.19-.43.43-.43h5.01l.12,3.48c0,.79.64,1.43,1.41,1.43h0l3.29.12s.01,0,.02,0c.05,0,.09-.01.13-.03v6.56c0,.24-.19.43-.43.43Z"/><path class="cls-1" d="m10.54,8.46h-4.88c-.28,0-.5.22-.5.5s.22.5.5.5h4.88c.28,0,.5-.22.5-.5s-.22-.5-.5-.5Z"/><path class="cls-1" d="m10.54,10.74h-4.88c-.28,0-.5.22-.5.5s.22.5.5.5h4.88c.28,0,.5-.22.5-.5s-.22-.5-.5-.5Z"/></svg>`,
                  displaytype : 'External Resource'};
        default:
          return {};
      }
    }
  
    addlistener(materialData, handle){
      var panelID = materialData.panelId;
      var materialID = materialData.id;
      var materialType = materialData.type;
      var displayname = materialData.displayname;
      var workspaceId = materialData.workspaceid;
      var scope = materialData.scope;
      handle.showselfhelpPopup();
      switch (materialType.toLowerCase()) {
        case "walkthrough":
          handle.triggerWalkthrough(handle,materialID, "selfhelp", panelID, scope);
          break;
        case "interactivevideo":
          handle.openInteractiveVideo(handle,materialID,workspaceId,displayname,panelID);
          break;
        case "guide":
          handle.openGuide(handle,materialID,workspaceId,panelID);
          break;
        case "externalcontent":
          handle.openExternalContent(handle,materialID,workspaceId,displayname,panelID);
          break;
        default:
          break;
      }
    }

  triggerWalkthrough(handle,materialID,medium, panelID, scope) {
    handle.walkthroughInstance.triggerFlow(materialID,medium, panelID, scope);
  }
  openInteractiveVideo(handle,materialID,workspaceId,displayname,panelID){
    this.createIframeForInteractivevideo(handle,materialID,workspaceId,displayname,panelID);
  }
  openGuide(handle,materialID,workspaceId,panelID){
    //this.openGuideInNewtab(handle,materialID,workspaceId,panelID);
    this.createIframeForGuide(handle,materialID,workspaceId,panelID);
  }
  openGuideInNewtab(handle,materialID,workspaceId,panelID){
    var domainConf = this.domainConf;
    var domain = window.location.protocol + "//" + (domainConf.domain[domainConf.domainType] ? domainConf.domain[domainConf.domainType] : document.domain);
    var url = domain + (handle.scope == "Enterprise" ? '/dap/guide/' + domainConf.servicename + '/' + workspaceId + '/' + materialID + 
               ((panelID !== undefined && panelID !== -1)
                            ? '/' + panelID
                            : '/preview') :
    '/mics/guide/' + domainConf.servicename + '/' + materialID);
    window.open(url, "_blank");
  }
  openExternalContent(handle,materialID,workspaceid,displayname,panelID){
    this.createIframeForExternalContent(handle,materialID,workspaceid,displayname,panelID);
  }
  createIframeForExternalContent(handle,materialID,workspaceId,displayname,panelID){
    var domainConf = handle.domainConf;
    var domain =  window.location.protocol + "//" + ( domainConf.domain[domainConf.domainType] ?  domainConf.domain[domainConf.domainType]  : document.domain) ;
    var Contenturl = domain + (handle.scope == "Enterprise" ? '/dap/externallink/' + domainConf.servicename + '/' + workspaceId + '/' + materialID + 
         ((panelID !== undefined && panelID !== -1)
                            ? '/' + panelID
                            : '/preview')
        + '?frameorigin='+window.location.protocol + "//" + document.domain : 
                    '/mics/externallink/' + domainConf.servicename + '/' + materialID + '?frameorigin=' +  document.domain);

    var iframePopupHTML = `
      <div id="dapContentOverlay">
        <div id="dapContentFrameContainer"> 
          <div id="dapContentHeader">
            <div id="dapContentHeader_left">         
<svg id="Layer_1" version="1.1" viewBox="0 0 1024 1024"> <defs>    <style>      .st0 {        fill: #f9b21d;      }      .st1 {        fill: #e42527;      }      .st2 {        fill: #226db4;      }      .st3 {        fill: #089949;      }    </style>  </defs>  <path class="st3" d="M30.5,1023.5c-6.8,0-13.6-2.3-19.2-7-12.7-10.6-14.3-29.5-3.7-42.2l290.9-346.7c11.4-13.6,28.2-21.4,45.9-21.4s34.5,7.8,45.9,21.4l97.1,115.8s0,0,0,0l173.3-206.6c10.6-12.7,29.5-14.3,42.2-3.7,12.7,10.6,14.3,29.5,3.7,42.2l-173.4,206.6c-11.4,13.6-28.2,21.4-45.9,21.4s-34.5-7.8-45.9-21.4l-97.1-115.8s0,0,0,0L53.5,1012.8c-5.9,7.1-14.4,10.7-23,10.7Z"></path>  <path class="st1" d="M30.5,1023.5c-16.6,0-30-13.4-30-30V414.2c0-66.2,53.8-120,120-120h470.9c16.6,0,30,13.4,30,30s-13.4,30-30,30H120.5c-33.1,0-60,26.9-60,60v579.3c0,16.6-13.4,30-30,30Z"></path>  <path class="st2" d="M838.7,250.3c-68.9,0-124.9-56-124.9-124.9S769.8.5,838.7.5s124.9,56,124.9,124.9-56,124.9-124.9,124.9ZM838.7,60.5c-35.8,0-64.9,29.1-64.9,64.9s29.1,64.9,64.9,64.9,64.9-29.1,64.9-64.9-29.1-64.9-64.9-64.9Z"></path>  <path class="st2" d="M993.5,726.6c-16.6,0-30-13.4-30-30v-282.4c0-33.1-26.9-60-60-60h-129.7c-33.1,0-60,26.9-60,60v19.9c0,16.6-13.4,30-30,30s-30-13.4-30-30v-19.9c0-66.2,53.8-120,120-120h129.7c66.2,0,120,53.8,120,120v282.4c0,16.6-13.4,30-30,30Z"><svg id="Layer_1" version="1.1" viewBox="0 0 1024 1024">  <!-- Generator: Adobe Illustrator 29.0.0, SVG Export Plug-In . SVG Version: 2.1.0 Build 186)  -->  <defs>    <style>      .st0 {        fill: #f9b21d;      }      .st1 {        fill: #e42527;      }      .st2 {        fill: #226db4;      }      .st3 {        fill: #089949;      }    </style>  </defs>  <path class="st3" d="M30.5,1023.5c-6.8,0-13.6-2.3-19.2-7-12.7-10.6-14.3-29.5-3.7-42.2l290.9-346.7c11.4-13.6,28.2-21.4,45.9-21.4s34.5,7.8,45.9,21.4l97.1,115.8s0,0,0,0l173.3-206.6c10.6-12.7,29.5-14.3,42.2-3.7,12.7,10.6,14.3,29.5,3.7,42.2l-173.4,206.6c-11.4,13.6-28.2,21.4-45.9,21.4s-34.5-7.8-45.9-21.4l-97.1-115.8s0,0,0,0L53.5,1012.8c-5.9,7.1-14.4,10.7-23,10.7Z"></path>  <path class="st1" d="M30.5,1023.5c-16.6,0-30-13.4-30-30V414.2c0-66.2,53.8-120,120-120h470.9c16.6,0,30,13.4,30,30s-13.4,30-30,30H120.5c-33.1,0-60,26.9-60,60v579.3c0,16.6-13.4,30-30,30Z"></path>  <path class="st2" d="M838.7,250.3c-68.9,0-124.9-56-124.9-124.9S769.8.5,838.7.5s124.9,56,124.9,124.9-56,124.9-124.9,124.9ZM838.7,60.5c-35.8,0-64.9,29.1-64.9,64.9s29.1,64.9,64.9,64.9,64.9-29.1,64.9-64.9-29.1-64.9-64.9-64.9Z"></path>  <path class="st2" d="M993.5,726.6c-16.6,0-30-13.4-30-30v-282.4c0-33.1-26.9-60-60-60h-129.7c-33.1,0-60,26.9-60,60v19.9c0,16.6-13.4,30-30,30s-30-13.4-30-30v-19.9c0-66.2,53.8-120,120-120h129.7c66.2,0,120,53.8,120,120v282.4c0,16.6-13.4,30-30,30Z"></path>  <path class="st0" d="M903.5,1023.5H170.5c-16.6,0-30-13.4-30-30s13.4-30,30-30h733c33.1,0,60-26.9,60-60v-206.9c0-16.6,13.4-30,30-30s30,13.4,30,30v206.9c0,66.2-53.8,120-120,120Z"></path></svg></path>  <path class="st0" d="M903.5,1023.5H170.5c-16.6,0-30-13.4-30-30s13.4-30,30-30h733c33.1,0,60-26.9,60-60v-206.9c0-16.6,13.4-30,30-30s30,13.4,30,30v206.9c0,66.2-53.8,120-120,120Z"></path></svg>
            <span id="text">${displayname}</span>
            </div>
            <div id="dapContentHeader_right">
              <svg id="closableIcon" viewBox="-3 -3 30 30" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M18 6L6 18M6 6l12 12"></path>
              </svg>
            </div>
          </div>
          <iframe src="${Contenturl}"></iframe>
        </div>
      </div>`;

    document.body.insertAdjacentHTML('beforeend', iframePopupHTML);
    document.querySelector("#dapContentOverlay > #dapContentFrameContainer > #dapContentHeader > #dapContentHeader_right >#closableIcon").onclick = function () {
    document.querySelector('#dapContentOverlay').remove();
    if (selfhelpsdk && selfhelpsdk.instance) selfhelpsdk.instance.onContentClose('externalContent', materialID);
    };
  }
    createIframeForInteractivevideo(handle,materialID,workspaceId,displayname,panelID) {
      var domainConf = handle.domainConf;
      var domain =  window.location.protocol + "//" + ( domainConf.domain[domainConf.domainType] ?  domainConf.domain[domainConf.domainType]  : document.domain) ;
      var videoUrl = domain + (handle.scope == "Enterprise" ? '/dap/interactivevideo/' + domainConf.servicename + '/' + workspaceId + '/' + materialID + 
         ((panelID !== undefined && panelID !== -1)
                            ? '/' + panelID
                            : '/preview')
        + '?frameorigin='+window.location.protocol + "//" + document.domain : 
                    '/mics/interactivevideo/' + domainConf.servicename + '/' + materialID + '?frameorigin=' +  document.domain);
      
      var iframePopupHTML = `
        <div id="dapVideoOverlay">
          <div id="dapVideoFrameContainer"> 
            <div id="dapVideoHeader">
              <div id="dapVideoHeader_left">         
                <svg viewBox="0 0 122 118" class="materialdesign"><path d="M5 76.4456V17C5 10.3726 10.3726 5 17 5H105C111.627 5 117 10.3726 117 17V76.4456C117 83.073 111.627 88.4456 105 88.4456H75.7959C73.7177 88.4456 71.721 89.2543 70.2286 90.7006L48.1613 112.085C47.4905 112.735 46.3738 112.192 46.4708 111.263L47.9304 97.2759C48.423 92.5548 44.7203 88.4456 39.9736 88.4456H17C10.3726 88.4456 5 83.073 5 76.4456Z" fill="none" stroke-width="8"></path><path fill="none" d="M48 62.6646V32.3034C48 30.8006 49.5954 29.8346 50.9271 30.5312L79.6472 45.5553C81.0709 46.3001 81.0796 48.3348 79.6622 49.0917L50.9421 64.4288C49.6099 65.1403 48 64.175 48 62.6646Z" stroke-width="8"></path></svg>
                <span id="text">${displayname}</span>
              </div>
              <div id="dapVideoHeader_right">
                <svg id="closableIcon" viewBox="-3 -3 30 30" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M18 6L6 18M6 6l12 12"></path>
                </svg>
              </div>
            </div>
            <iframe src="${videoUrl}"></iframe>
          </div>
        </div>`;
  
      document.body.insertAdjacentHTML('beforeend', iframePopupHTML);
      document.querySelector("#dapVideoOverlay > #dapVideoFrameContainer > #dapVideoHeader > #dapVideoHeader_right >#closableIcon").onclick = function () {
        document.querySelector('#dapVideoOverlay').remove();
        if (selfhelpsdk && selfhelpsdk.instance) selfhelpsdk.instance.onContentClose('interactivevideo', materialID);
      };
    }

    createIframeForGuide(handle,materialID,workspaceId,panelID) {
      var domainConf = handle.domainConf;
      var domain =  window.location.protocol + "//" + ( domainConf.domain[domainConf.domainType] ?  domainConf.domain[domainConf.domainType]  : document.domain) ;
      var guideUrl = domain + (handle.scope == "Enterprise" ? '/dap/guide/' + domainConf.servicename + '/' + workspaceId + '/' + materialID + 
        ((panelID !== undefined && panelID !== -1)
                            ? '/' + panelID
                            : '/preview')
        + '?frameorigin='+window.location.protocol + "//" + document.domain : 
                    '/mics/guide/' + domainConf.servicename + '/' + materialID + '?frameorigin=' +  document.domain);
            
      var iframePopupHTML = `
          <div id="dapGuideOverlay">
          <div id="dapGuideFrameContainer"> 
              <div id="dapGuideHeader">
              <div id="dapGuideHeader_left">         
                  <svg viewBox="0 0 16 16" width="20" height="20" class="materialdesign"><defs><style>.cls-1{stroke-width:0px;}</style></defs><path class="cls-1" d="m13.73,5.56l-3.81-4.02c-.33-.35-.79-.54-1.26-.54H3.22c-.79,0-1.43.64-1.43,1.43v11.14c0,.79.64,1.43,1.43,1.43h9.55c.79,0,1.43-.64,1.43-1.43v-6.81c0-.45-.17-.87-.48-1.2Zm-.94.46l-3-.11c-.24,0-.43-.19-.43-.45l-.11-3.18,3.54,3.74Zm-.01,7.98H3.22c-.24,0-.43-.19-.43-.43V2.43c0-.24.19-.43.43-.43h5.01l.12,3.48c0,.79.64,1.43,1.41,1.43h0l3.29.12s.01,0,.02,0c.05,0,.09-.01.13-.03v6.56c0,.24-.19.43-.43.43Z"/><path class="cls-1" d="m10.54,8.46h-4.88c-.28,0-.5.22-.5.5s.22.5.5.5h4.88c.28,0,.5-.22.5-.5s-.22-.5-.5-.5Z"/><path class="cls-1" d="m10.54,10.74h-4.88c-.28,0-.5.22-.5.5s.22.5.5.5h4.88c.28,0,.5-.22.5-.5s-.22-.5-.5-.5Z"/></svg>
                  <span id="text" >Guide</span>
              </div>
              <div id="dapGuideHeader_right" style="cursor:pointer;display:flex;align-items:center;">
                  <svg id="closableIconGuide" viewBox="-3 -3 30 30"  stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M18 6L6 18M6 6l12 12"></path>
                  </svg>
              </div>
              </div>
              <iframe src="${guideUrl}" allowfullscreen allow="fullscreen"></iframe>
          </div>
          </div>`;
  
      document.body.insertAdjacentHTML('beforeend', iframePopupHTML);
      document.querySelector("#dapGuideOverlay > #dapGuideFrameContainer > #dapGuideHeader > #dapGuideHeader_right > #closableIconGuide").onclick = function () {
          document.querySelector('#dapGuideOverlay').remove();
          if (selfhelpsdk && selfhelpsdk.instance) selfhelpsdk.instance.onContentClose('guide', materialID);
            };
            }


    applyplaceholderstyles(){
      var micsselfhelptoggler = document.querySelector("#micsselfhelptoggler");
      micsselfhelptoggler.style[this.stylereference.backgroundcolor]=this.styleforDefaultplaceholder.backgroundcolor;
      micsselfhelptoggler.style[this.stylereference.fontColor]=this.styleforDefaultplaceholder.fontColor;
      micsselfhelptoggler.style[this.stylereference.fontSize]=this.styleforDefaultplaceholder.fontSize;
      micsselfhelptoggler.style[this.stylereference.fontFamily]=this.styleforDefaultplaceholder.fontFamily;
      micsselfhelptoggler.style[this.stylereference.borderRadius]=this.styleforDefaultplaceholder.borderRadius;
      micsselfhelptoggler.style[this.stylereference.width]=this.styleforDefaultplaceholder.width;
      micsselfhelptoggler.style[this.stylereference.height]=this.styleforDefaultplaceholder.height;
    }
    
    applypopupstyles(){
    
      var micsselfhelpContainer= document.querySelector("#micsselfhelpContainer");
      micsselfhelpContainer.style[this.stylereference.backgroundcolor]=this.styleforselfhelppopup.home.backgroundcolor;
      micsselfhelpContainer.style[this.stylereference.fontFamily]=this.styleforselfhelppopup.home.fontFamily;
      micsselfhelpContainer.style[this.stylereference.boxShadow]=this.styleforselfhelppopup.home.boxShadow;
    
      var topbar= document.querySelector("#micsselfhelpContainer > #topbar");
      topbar.style[this.stylereference.backgroundcolor]=this.styleforselfhelppopup.topband.backgroundcolor;
      topbar.style[this.stylereference.fontFamily]=this.styleforselfhelppopup.topband.fontFamily;
      topbar.style[this.stylereference.fontWeight]=this.styleforselfhelppopup.topband.fontWeight;
      topbar.style[this.stylereference.fontSize]=this.styleforselfhelppopup.topband.fontSize;
      topbar.style[this.stylereference.boxShadow]=this.styleforselfhelppopup.topband.boxShadow;
      topbar.style[this.stylereference.height]=this.styleforselfhelppopup.topband.height;
    
      var topbartext= document.querySelector("#micsselfhelpContainer > #topbar > #helphublogotextcontainer > #text");
      topbartext.style[this.stylereference.fontColor]=this.styleforselfhelppopup.topband.fontColor;
    
      var closeicon= document.querySelector("#micsselfhelpContainer > #topbar > #micsselfhelpclosableIcon");
      closeicon.style[this.stylereference.iconColor]=this.styleforselfhelppopup.closebutton.iconColor;
      closeicon.style[this.stylereference.iconSize]=this.styleforselfhelppopup.closebutton.iconSize;
    
      var searchbar= document.querySelector("#materiallistsearchbar");
      searchbar.style[this.stylereference.backgroundcolor]=this.styleforselfhelppopup.searchbar.backgroundcolor;
      searchbar.style[this.stylereference.borderRadius]=this.styleforselfhelppopup.searchbar.borderRadius;
      searchbar.style[this.stylereference.border]=this.styleforselfhelppopup.searchbar.border;
      
      var searchicon= document.querySelector("#materiallistsearchbar > #searchicon");
      searchicon.style[this.stylereference.iconSize]=this.styleforselfhelppopup.searchbar.iconSize;
      searchicon.style[this.stylereference.iconColor]=this.styleforselfhelppopup.searchbar.iconColor;
    
      var searchinput= document.querySelector("#materiallistsearchbar > #micsselfhelpsearchinput");
      searchinput.style[this.stylereference.fontColor]=this.styleforselfhelppopup.searchbar.fontColor;
      this.setdynamicstyleforlist()
    
    }
    
    setdynamicstyleforlist(){
      var listitemhover= document.querySelectorAll(".flowlist");
      var handle=this;
      listitemhover.length?listitemhover.forEach(material => {
        material.onmouseover = function() {
            material.style[handle.stylereference.backgroundcolor] = handle.styleforselfhelppopup.listitemhover.backgroundcolor;
          //   material.style[handle.stylereference.fontColor] = handle.styleforselfhelppopup.listitemhover.fontColor;
        };
        material.onmouseout = function() {
            material.style[handle.stylereference.backgroundcolor] = handle.styleforselfhelppopup.listitem.backgroundcolor;
            material.style[handle.stylereference.fontColor] = handle.styleforselfhelppopup.listitem.fontColor;
        };
      material.style[this.stylereference.backgroundcolor]=this.styleforselfhelppopup.listitem.backgroundcolor;
      material.style[this.stylereference.fontColor]=this.styleforselfhelppopup.listitem.fontColor;
      material.style[this.stylereference.height]=this.styleforselfhelppopup.listitem.height;
      material.style[this.stylereference.fontSize]=this.styleforselfhelppopup.listitem.fontSize;
      material.style[this.stylereference.fontFamily]=this.styleforselfhelppopup.listitem.fontFamily;
      material.style[this.stylereference.fontWeight]=this.styleforselfhelppopup.listitem.fontWeight;


      const materialType = material.querySelector("#materialtype");
      if (materialType) materialType.style[this.stylereference.fontColor] = this.styleforselfhelppopup.topband.backgroundcolor;

      const materialIcon = material.querySelector(".materialicon");
      if (materialIcon) materialIcon.style[this.stylereference.backgroundcolor] = this.styleforselfhelppopup.topband.backgroundcolor;
            
      const materialDesign = material.querySelector(".materialdesign");
      if (materialDesign) {
        materialDesign.style['stroke'] = "#ffffff";
        materialDesign.style['fill'] = "#ffffff";
      }

      const walkthrouhiconinnerfill = material.querySelector(".walkthrouhiconinnerfill");
      if (walkthrouhiconinnerfill) {
        walkthrouhiconinnerfill.style['fill']= this.styleforselfhelppopup.topband.fontColor;
      }
    }):"";
    }
  
  updatedefaultjson(target, source) {
    for (const key in source) {
        if (source[key] instanceof Object && key in target) {
            Object.assign(source[key], this.updatedefaultjson(target[key], source[key]));
        }
    }
    Object.assign(target || {}, source);
    return target;
  }
  
  
  materialsearch(handle){

      var searchvalue=document.getElementById('micsselfhelpsearchinput').value.trim().toLowerCase();

      var materiallistid = document.getElementById('materiallistcontainer');
      
      let nodataDiv = handle.utility.createEmptyStateDiv(document, handle.styleforselfhelppopup.noitem, handle.selfhelpcontents.searchnotfound);

      let errorDiv = handle.utility.createEmptyStateDiv(document, handle.styleforselfhelppopup.noitem, 'Something went wrong! Please try again later.');

      if(searchvalue===''){
				materiallistid.innerHTML = ''
        handle.addListInMaterial();
        clearTimeout(this.searchTimeout);
        return;
      }
  
      clearTimeout(this.searchTimeout); // kill the running timeout

      this.searchTimeout = setTimeout(()=>{        // start new timeout to make a call for suggestion

          let loaderDiv = handle.utility.createLoader(document);

          materiallistid.innerHTML = '';
          materiallistid.appendChild(loaderDiv);

          var suggestionlist = [];

          var self = handle;

          var params = {
            "orgid": handle.orgid,
            "serviceid": handle.serviceid,
            "searchkey": searchvalue,
            "action":"getKeyWordMatchingMaterials",
            "Scope": handle.scope,
          }

          if(handle.verification){
            params["materialidlist"] =  JSON.stringify(Object.keys(handle.materialMap));
          }

					handle.utility.getSuggestion(handle.micssdktoserverInstance, params, "get", orgsuccess, orgerror);

					function orgsuccess(xhttp){
						try {
							if(searchvalue == document.getElementById('micsselfhelpsearchinput').value.trim().toLowerCase()){
								suggestionlist = JSON.parse(xhttp);
								if(suggestionlist.length != 0){
										let fragment = document.createDocumentFragment();
										for(let i=0; i<suggestionlist.length; i++){

											let materialData = handle.materialMap[suggestionlist[i]];

											let flowDiv = handle.utility.createFlowlist(document, materialData, handle);

											fragment.appendChild(flowDiv);

											materialData.type =="walkthrough" ? handle.getallwalkthroughid[materialData.scope].push(materialData.id) : "";   
										}
				
										materiallistid.innerHTML = '';
										fragment.childNodes.length > 0 ? materiallistid.appendChild(fragment) : materiallistid.appendChild(nodataDiv);
										self.setdynamicstyleforlist();
								}
								else{
										materiallistid.innerHTML = '';
										materiallistid.appendChild(nodataDiv);
								}

								handle.walkthroughInstance.loadFlow(handle.getallwalkthroughid["Service"],"Service");
								handle.walkthroughInstance.loadFlow(handle.getallwalkthroughid["Enterprise"],"Enterprise");

								if(document.getElementById('micsselfhelpsearchinput').value.trim().toLowerCase() === ''){ 
                    handle.addListInMaterial();
								}
							}
						}
						catch(e){
							materiallistid.innerHTML = '';
							materiallistid.appendChild(errorDiv);
						}
							
					}

					function orgerror(xhttp){ 
						materiallistid.innerHTML = '';
						materiallistid.appendChild(errorDiv);
					}

          }, 500);

  }


  showMaterialContainerWithEffect() {
    document.getElementById("micsselfhelpContainer").style.display = 'flex';
    setTimeout(() => {
      document.getElementById("micsselfhelpContainer").classList.add("showmicsselfhelpContainer");
    }, 300);
  }

  hideMaterialContainerWithEffect() {
    document.getElementById("micsselfhelpContainer").classList.remove("showmicsselfhelpContainer");
    setTimeout(() => {
      document.getElementById("micsselfhelpContainer").style.display = 'none';
    }, 500);
  }

  showSelfhelpButtonwithEffect() {
    setTimeout(() => {
      document.getElementById("selfhelpicon").style.display = 'block';
      document.getElementById("selfhelpicon").classList.add("showselfhelpicon");
    }, 550);
  }

  hideSelfhelpButtonwithEffect() {
    document.getElementById("selfhelpicon").classList.remove("showselfhelpicon");
    setTimeout(() => {
      document.getElementById("selfhelpicon").style.display = 'none';
    }, 550);
  }
  }
/*$Id$*/
class bannersdklocalstoragemanager {
    constructor() {
        this.micssdkstorage = this.getinlocalstorage("micssdkstorage");
        this.bannerloadtimeforORG=this.getinlocalstorage("bannerloadtime");
        this.statsavailable=["received","clicked","closed"];
        if (!this.micssdkstorage) {
            this.micssdkstorage = { banner: {} };
            this.notifybanner(this.micssdkstorage);
        }
        if(!this.bannerloadtimeforORG){
            this.bannerloadtimeforORG={};
            this.setinlocalstorage("bannerloadtime",this.bannerloadtimeforORG);
        }
    }
    reservespaceforORG(orgid) {
        if (!this.micssdkstorage.banner[orgid]) {
            this.micssdkstorage.banner[orgid] = [];
            this.notifybanner(this.micssdkstorage);
        }
        return true;
    }
    notifybanner(bannerdata){
        this.setinlocalstorage("micssdkstorage", bannerdata);
    }
   checkbannerid(orgid, bannerid) {
        this.micssdkstorage = this.getinlocalstorage("micssdkstorage");
           const item = this.micssdkstorage?.banner?.[orgid]?.[0];
           if (!item) {
            return true;
            }
            if(item.data?.PromotionID === bannerid ){
                if(this.checkbannervalidation(orgid) === false){//if click or close before return false.
                    return false;
                }
            }
            return this.checkbannerexpired(orgid); //check expired
        }
    
   checkbannerexpired(orgid){
        this.bannerloadtimeforORG=this.getinlocalstorage("bannerloadtime");
            const orgData = this.bannerloadtimeforORG?.[orgid];
            const isExpired = !orgData || (Date.now() - orgData.loadedtime) >= orgData.buffertime;
            return isExpired; 
        }
   enqueMessage(orgid, banner, buffertime) {
        this.reservespaceforORG(orgid);
        if (this.checkbannerid(orgid, banner.PromotionID) && this.visibilitycheck() && this.setbannerloadtimeinlocalstorage(orgid,banner.PromotionID,buffertime)) { 
            this.micssdkstorage.banner[orgid][0] = {
                data: banner,
                received: false,
                clicked: false,
                closed: false
            };
            this.notifybanner(this.micssdkstorage);
        }
    }
    dequeMessage(orgid, bannerid) {
        if (this.visibilitycheck()) {
            this.micssdkstorage.banner[orgid][0] = {};
            this.notifybanner(this.micssdkstorage);
            return false;
        }
        return true;
        
    }
    addMetrics(orgid, bannerid, key, value, time) {
    }
    getMetrics(orgid){
        this.micssdkstorage = this.getinlocalstorage("micssdkstorage");
        const item = this.micssdkstorage.banner[orgid]?.[0];
      const statswithbannerid={"stats":[]};
        if (this.visibilitycheck() && item && item.data?.PromotionID) {
            statswithbannerid.bannerid = item.data.PromotionID;
          statswithbannerid.scope = item.data.scope;
            for(let statsvalue of this.statsavailable){
                if(item[statsvalue]){
                    statswithbannerid.stats.push(statsvalue);
                }
            }
        }
  	return statswithbannerid;
    }
    updateMetrics(orgid, bannerid, key, value) {
        this.micssdkstorage = this.getinlocalstorage("micssdkstorage");
        const item = this.micssdkstorage.banner[orgid]?.[0];
        if (this.visibilitycheck() && item && item.data?.PromotionID === bannerid ) {
            item[key] = value;
            this.notifybanner(this.micssdkstorage);
        }
    }
    setCallbackListenser(localstoragekey, callbackFunction, instance) {
        window.addEventListener("storage", (event) => {
            if (event.key === localstoragekey) {
                callbackFunction(this.parsevalue(event.newValue),instance);
            }
        });
    }
    checkbannervalidation(orgid) {
        this.micssdkstorage = this.getinlocalstorage("micssdkstorage");
        const bannertemp = this.micssdkstorage.banner[orgid]?.[0];
        if (bannertemp && bannertemp.data?.PromotionID) {
            return (!bannertemp.closed && !bannertemp.clicked);
        }
        return false;
    }
    checkbannersendstats(orgid, bannerid) {
        this.micssdkstorage = this.getinlocalstorage("micssdkstorage");
        const bannertemp = this.micssdkstorage.banner[orgid]?.[0];
        if (bannertemp && bannertemp.data?.PromotionID === bannerid) {
             return ( bannertemp.closed ? 'closed' : bannertemp.clicked ? 'clicked' : bannertemp.received ? 'received' : 'load' );
        }
        return false;
    }
    checkbannerinlocalstorage(orgid) {
        this.micssdkstorage = this.getinlocalstorage("micssdkstorage");
        const bannertemp = this.micssdkstorage.banner[orgid]?.[0];
        if (bannertemp && this.checkbannervalidation(orgid) && !this.checkbannerexpired(orgid)) {
            return this.stringifyvalue(bannertemp.data);
        }
        return null;
    }
    parsevalue(value) {
        try {
            return JSON.parse(value);
        } catch {
            return null;
        }
    }
    stringifyvalue(value) {
        return JSON.stringify(value);
    }
    setinlocalstorage(key, value) {
        if(this.visibilitycheck()){
        localStorage.setItem(key, this.stringifyvalue(value));
        }
        return;
    }
    getinlocalstorage(key) {
        return this.parsevalue(localStorage.getItem(key));
    }
    visibilitycheck(){
        return (document.visibilityState === "visible");
    }
    setbannerloadtimeinlocalstorage(orgid,bannerid,buffertime){
        this.bannerloadtimeforORG=this.getinlocalstorage("bannerloadtime");
        if(!this.visibilitycheck()){
            return false;
        }
        if(this.bannerloadtimeforORG[orgid]?.bannerid){
            if(((Date.now() - this.bannerloadtimeforORG[orgid].loadedtime ) < this.bannerloadtimeforORG[orgid].buffertime))
            {
                return false;
            }
        }
        this.bannerloadtimeforORG[orgid]={"loadedtime":Date.now(),"bannerid":bannerid,"buffertime":buffertime};
        this.setinlocalstorage("bannerloadtime",this.bannerloadtimeforORG);
        return true;
    }
  checkbannerloadtimeonly(orgid){
   let timecheck = ((Date.now() - this.bannerloadtimeforORG[orgid]?.loadedtime ) > this.bannerloadtimeforORG[orgid]?.buffertime);
         return timecheck;
  
    }
    getbannerloadtimeinlocalstorage(orgid,bannerid){
	this.bannerloadtimeforORG=this.getinlocalstorage("bannerloadtime");
        var orgcheck = this.bannerloadtimeforORG[orgid];
        var samebanner = false;
    	if(!orgcheck){
            return true;
        }
        if(this.bannerloadtimeforORG[orgid]?.bannerid === bannerid && this.checkbannervalidation(orgid)){
              samebanner =true; 
        }
        var timechecker = samebanner || this.checkbannerloadtimeonly(orgid);
        return timechecker;
    }
  }
  
// //$Id$
// class WmsCallback {
//     constructor() { }
//     handleMessages(prd, msg) {
//         if (prd == 'MI' && msg["inproduct.messages"] == 'Banner' && msg.payload && msg.payload['mics.data']) {
//             this.handleServerStatus(true, msg);
//             window.postMessage({ emittype: 'bannerMsgFromWms', msg: msg }, "*");
//         }
//         else if (msg["inproduct.messages"] == "MessageBoard" && msg.payload && msg.payload['mics.pid']) {
//             window.postMessage({ emittype: 'messageboardMsgFromWms', msg: msg }, "*");
//         }
//     }
//     handleServerStatus(isUp, msg) {
//         window.postMessage({ emittype: 'bannerServerupFromWms', "serverup": isUp }, "*");
//         window.postMessage({ emittype: 'messageboardServerupFromWms', "serverup": isUp }, "*");
//     }
//     intialize() {
//         var self = this;
//         setTimeout(function () {
//             if (typeof (WebMessanger) !== 'undefined' && (getWmsConfig() & WMSSessionConfig.CROSS_PRD) == WMSSessionConfig.CROSS_PRD) {
//                 WebMessanger.subscribeToCrossProductMessages(function (prd, msg) {
//                     self.handleMessages(prd, msg);
//                 });
//                 WebMessanger.subscribeToServerUp(function (prd, msg) {
//                     setTimeout(function () { self.handleServerStatus(true, msg); }, 10000)
//                 });
//                 WebMessanger.subscribeToServerDown(function (prd, msg) {
//                     self.handleServerStatus(false, msg);
//                 });
//             }
//             else if (typeof (WmsLite) !== 'undefined') {
//                 WmsLite.subscribeToCrossProductMessages(function (prd, msg) {
//                     self.handleMessages(prd, msg);
//                 });
//                 WmsLite.subscribeToServerUp(function (prd, msg) {
//                     setTimeout(function () { self.handleServerStatus(true, msg); }, 10000)
//                 });
//                 WmsLite.subscribeToServerDown(function (prd, msg) {
//                     self.handleServerStatus(false, msg);
//                 });
//             }
//         }, 1000);
//     }
// }
// var wms = new WmsCallback();
// wms.intialize();//$Id$

class InproductHttpCall
{
/** Extremely Important **/
/** Please refrain from using async = false. **/ 
/** Executing http calls syncronously will cause the entire page to freeze. **/
    static logger =null;

	constructor(http_method, path, headers, params, async, domain)
	{
		this.xhr = new XMLHttpRequest();
		this.http_method = http_method;
		this.domain = domain;
		this.path = this.setPath(path);
		this.headers = headers;
		this.params = params;
		this.async = async;
		this.isMicsE=false;
		this.setDefaultErrorConfiguration();
        if(InproductHttpCall.logger===null){
            InproductHttpCall.logger= InproductLogger.getInstance();
        }
	}

	setRequestBody(body) // body must be in string. We dont support FormData(), blob etc
 	{
		this.body = body;
	}
	setPath(path){
		return this.domain ?this.domain + path :sessionStorage.isbrandeddomain ? location.protocol + '//' + location.host + '/micse' + path  : location.protocol + '//' + location.host + path; // Checking the type of domain to make request respectively.
	}   
	setStaticPath(path)
       {
                this.path = path;
       }
	makeHttpRequest(onresponsecallback, onerrorcallback)
	{
		var queryparam="";	
		var self = this;
		for (let key of this.params.keys())
		{		
			queryparam+= (queryparam == "")?  (key +"="+encodeURIComponent(this.params.get(key))) : ("&"+key +"="+encodeURIComponent(this.params.get(key))) ;
		}
                this.xhr.open(this.http_method, (queryparam == "")? (this.path) : (this.path+"?"+queryparam), this.async);
		for (let key of this.headers.keys())
		{
			this.xhr.setRequestHeader(key, this.headers.get(key));
		}

		this.xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");

		if(this.http_method == "post" || this.http_method=="Post" || this.http_method =="POST")
		{       

                        var csrfToken =this.getCSRFTokenFromCookie();   
                        var csrfParam ="iamcsrcoo";
						var orgid=this.getOrgId();
                        var forMicsE=this.getForMicsE();

			if(this.body == undefined)
			{
				this.body= "";
			}
			if(this.isMicsE==true){
			this.body+= (this.body== "")? (csrfParam+"="+csrfToken+"&orgid="+orgid+"&forMicsE="+forMicsE) : ("&"+csrfParam+"="+csrfToken+"&orgid="+orgid+"&forMicsE="+forMicsE);
			}
			else{
				this.body+= (this.body== "")? (csrfParam+"="+csrfToken) : ("&"+csrfParam+"="+csrfToken);	
			}

		}
		this.xhr.onload = () => {
            var httpStatus = this.xhr.status;
            if (self.errorConfig.HttpError[httpStatus] && self.errorConfig.HttpError[httpStatus].onError) {
                    self.errorConfig.HttpError[httpStatus].onError(this.xhr); //should pass the logger info as func also  
            }
            else if(httpStatus!=200 && httpStatus!='200'){
                InproductHttpCall.logger.log("Response Error", "medium", "error in response");
            }
            if (typeof onresponsecallback === 'function') {
                onresponsecallback(this.xhr);
            }
        };

            this.xhr.onerror = function() {
                var httpStatus = this.xhr.status;
                if (self.errorConfig[httpStatus] && self.errorConfig[httpStatus].onError) {
                    self.errorConfig[httpStatus].onError(this.xhr); //should pass the logger info as func also  
                }
                else{
                    InproductHttpCall.logger.log("Network Error", "high", "Not reachable");
                }
                if (typeof onerrorcallback === 'function') {
                onerrorcallback(this);
                }
            }
            if(this.body == undefined)
            {
                this.xhr.send();
            }
            else
            {
                this.xhr.send(this.body);
            }
	    }

        getCSRFTokenFromCookie() {
                var ca = document.cookie.split(';');
                var csr={}
                for (var i = 0; i < ca.length; i++) {
                        var c = ca[i].trim();
                        c=c.split('=');
                        csr[c[0]]=c[1]
                }
                return csr.iamcsr;
        }
        
        getOrgId(){
              var orgid=sessionStorage.getItem("orgid");
			  if(orgid==null){
				return -1
			  }
			  else{
              return orgid;
			  }
        }
        
        getForMicsE(){
              var forMicsE=sessionStorage.getItem("forMicsE");
			  if(forMicsE==null){
				return false;
			  }
              return forMicsE;
        }
         
        forMicsE(boolean){
            if(boolean==true){
            this.isMicsE=true;
                }
                else{
                    this.isMicsE=false;
                }
            }

		setCustomErrorConfiguration(errorConfig){
			this.errorConfig = errorConfig;
		}

		setCustomErrorConfigurationByType(errorConfigType,errorConfig){
			this.errorConfig[errorConfigType] = errorConfig;
		}

        setCustomOnHttpErrorConfigurationByType(key,errorConfig){
        this.errorConfig.HttpError[key]=errorConfig;
        }

		setCustomOnHttpErrorConfiguration(key,onError){
				this.errorConfig.HttpError[key].onError = onError;
		}

		setDefaultErrorConfiguration(){
			this.errorConfig = {
				NetworkError: {
					message: 'A network error occurred',
					code: 'NET_ERR',
					severity: 'high',
					retryable: true,
					onError: null  // Custom error handler
				},
				TimeoutError: {
					message: 'Request timed out',
					code: 'TIMEOUT_ERR',
					severity: 'medium',
					retryable: true,
					onError: null
				},
				HttpError: {
					'400': {
						message: 'Bad Request - Invalid input',
						code: 'BAD_REQ',
						severity: 'medium',
						retryable: false,
						onError: null
					},
					'401': {
						message: 'Unauthorized - Authentication required',
						code: 'UNAUTH',
						severity: 'high',
						retryable: false,
						onError: null
					},
					'403': {
						message: 'Forbidden - Insufficient permissions',
						code: 'FORBIDDEN',
						severity: 'high',
						retryable: false,
						onError: null
					},
					'404': {
						message: 'Not Found - Resource doesn\'t exist',
						code: 'NOT_FOUND',
						severity: 'medium',
						retryable: false,
						onError: null
					},
					'500': {
						message: 'Internal Server Error',
						code: 'SERVER_ERR',
						severity: 'critical',
						retryable: true,
						onError: null
					}
				}
			}
		}
}

//$Id$
class InproductLogger {
            static instance;
            constructor(options = {}) {
              this.logCache = {
                low: [],
                medium: [],
                high: []
              };
              this.MAX_CACHE_SIZE = options.maxCacheSize || 100;
          
            }
          
            static getInstance(options = {}) {
              if (!InproductLogger.instance) {
                InproductLogger.instance = new InproductLogger(options);
              }
              return InproductLogger.instance;
            }
            normalizeMessage(message) {
              if (message instanceof Error) {
                return `${message.name}: ${message.message}${message.stack ? `\nStack: ${message.stack}` : ''}`;
              }
              if (typeof message === 'object') {
                try {
                  return JSON.stringify(message);
                } catch {
                  return message.toString();
                }
              }
              return String(message);
            }
          
            cacheLog(severity, logEntry) {
              if (this.logCache[severity].length >= this.MAX_CACHE_SIZE) {
                this.logCache[severity].shift(); // Remove oldest entry
              }
              this.logCache[severity].push(logEntry);
            }
            log(moduleName, severity, message) {
              if (!moduleName || !severity || message === undefined) {
                throw new Error('Invalid log parameters');
              }
          
              var normalizedSeverity = severity.toLowerCase();
          
              var logEntry = {
                timestamp: new Date().toISOString(),
                moduleName,
                severity,
                message: this.normalizeMessage(message)
              };
          
              switch (normalizedSeverity) {
                case 'low':
                case 'medium':
                case 'high':
                    this.cacheLog(normalizedSeverity, logEntry);
                    break;
                default:
                  throw new Error('Invalid severity level');
              }
            }
          
            getCachedLogs(severity) {
              var normalizedSeverity = severity.toLowerCase();
              return this.logCache[normalizedSeverity] || [];
            }
            
            getAllLogs(){
                return this.logCache;
            }
          
            clearCachedLogs(severity) {
              var normalizedSeverity = severity.toLowerCase();
              this.logCache[normalizedSeverity] = [];
            }
          
            clearAllLogs() {
              Object.keys(this.logCache).forEach(severity => {
                this.logCache[severity] = [];
              });
            }
          }
        
//  $Id$
// file for utility functions related to inproduct which can be used across different inproducts like banner, walkthrough etc. This will help us to avoid code duplication and maintain the code in a better way.

class Inproductutility {
  static appID = '';
  static clientportalID = '';
  static orgType = '';
  static dap_product_type = "";
  static userlang = "";
  static inproductinbundle = false;

  //function to check if the inproduct is running inside bundle or not. 
  // This will help us to decide the initialization of inproduct.

  static isInproductinbundle() {
    let windowvariableaccess = window.micsinproduct || {};
    Inproductutility.inproductinbundle = windowvariableaccess.isbundle || false;
    return Inproductutility.inproductinbundle;
  }

  // function to validate tipengine domain and add support for new tipengine domains without changing the code. This will help us to avoid code changes for new tipengine domains.

  static validateTipDomain(tipurlfromconf) {
    let tipEngineGroups = ['tipengine.', 'tipengine1.', 'tipengine2.', 'micstipenginetest1.', 'micstipenginetest2.', 'tipengine3.', 'tipenginetest1.', 'tipenginetest2.', 'tipengineqa1.'];
    let domaincopy = tipurlfromconf;
    let tipdomaingroupname = tipEngineGroups.find(group => domaincopy.includes(group)) || 'tipengine3.';
    let tipdomain = domaincopy.split('//')[1].replace(tipdomaingroupname, "").split('.').reverse();
    let currentdomain = (location.hostname).split('.').reverse();
    currentdomain = currentdomain.slice(0, tipdomain.length).join('');
    tipdomain = tipdomain.join('');
    return tipdomain === currentdomain
  }

  // function to get the domain type of the product. This will help us to decide the API path for the inproduct.

  static getDomainType(tipdomain, productdomain) {
    if (Inproductutility.validateTipDomain(tipdomain)) {
      return "zoho";
    } else if (productdomain.includes('manageengine') || location.hostname.includes('manageengine')) {
      return "manageengine";
    }
    return "";
  }

  // function to construct the API path for the inproduct. This will help us to decide the API path for the inproduct based on the domain type.

  static constructL7api(apiPath, tipdomain, prefixPath, forDap) {
    let domainType = Inproductutility.getDomainType(tipdomain, location.hostname);
    if (domainType === "") {
      apiPath = prefixPath + apiPath;
    }
    else if (domainType === "manageengine" && !forDap) {
      apiPath = prefixPath + apiPath;
    }
    return apiPath;
  }

  // function to set the appID and clientportalID for the inproduct. This will help us to initialize the inproduct with the correct appID and clientportalID for current instance.
  static setAppID(appID, orgType) {
    Inproductutility.appID = appID;
    Inproductutility.setOrgModelType(orgType);
  }

  static setClientPortalID(clientportalID, orgType) {
    Inproductutility.clientportalID = clientportalID;
    Inproductutility.setOrgModelType(orgType);
  }

  static setOrgModelType(orgType) {
    Inproductutility.orgType = orgType;
  }

  static setClientPortalAndAppID(clientportalID, appID, orgType) {
    Inproductutility.setAppID(appID, orgType);
    Inproductutility.setClientPortalID(clientportalID, orgType);
  }

  // function to set the product type for dap. This will help us to decide the API path for the inproduct based on the product type.
  static setDapProductType(type) {
    Inproductutility.dap_product_type = type;
  }

  // function to set the user language for the inproduct. This will help us to display the inproduct in the correct language for the user.
  static setUserLang(lang) {
    Inproductutility.userlang = lang;
  }

  static getUserLang() {
    return Inproductutility.userlang;
  }


  static getInproductConf() {
    return {
      "appID": Inproductutility.appID,
      "clientportalID": Inproductutility.clientportalID,
      "orgtype": Inproductutility.orgType,
      "product_type": Inproductutility.dap_product_type
    }
  }

  static validatePostMessageOrigin(event, type) {
     switch (type) {
        case "sameDomain":
          return  Inproductutility.validateTipDomain(event.origin) || event.origin === window.location.origin;
        case "openerDomain":
          return event.origin && Inproductutility.origincheck(event.origin);
        default:          
          return false;
     }
  }
  static origincheck(openerurl) {
        openerurl = openerurl.split(".");
        var domainnames = ["https://dap-sandbox","https://predap1","https://dap1","https://newdap", "https://mics", "https://dapnew","https://micse", "https://micsetest", "https://dap", "https://premics", "https://predap", "https://micsqa","https://dapqa","https://dapqa1","https://dapqa2","https://dapqa3","https://predaptest","https://daptest","https://daptest1","https://daptest2"]; //need an entry if domain added.
        var trustedsubdomains = ["zoho", "localzoho", "manageengine", "localmanageengine", "zohocloud", "zohonoc"];
        var testdomainstartswith = "micstest";
        return (trustedsubdomains.includes(openerurl[1]) && (domainnames.includes(openerurl[0]) || openerurl[0].includes(testdomainstartswith)));
  } 
  


}


// $Id$
class BuilderPreview {

    constructor(onEndPreview) {
        this.onEndPreviewCallback = onEndPreview;
        this.onGoingPreviewData;
        this.lastReceivedMetric = {
            stepnumber:1
        };
        this.elementsRef = {
            info: null,
            infoStyle: null
        };
        this.eventHandlers = this.getBoundMethodsRef();
        this.overWriteFunc = {
            "sendMetric": {
                "endTour": this.onMetricsReceived.bind(this),
                "error": this.onMetricsReceived.bind(this),
                "rendered": this.onMetricsReceived.bind(this),
                "completed": this.onMetricsReceived.bind(this),
                "quitted": this.onMetricsReceived.bind(this)
            }
        };
        this.clearListenersCallback = null;
        this.Util = WalkthroughBuilderSDKUtility;
        this.closedContainer = new InproductContainer('walkthrough-preview-info');
    }

    startPreview(firstStepUrl, walkthroughFlowData) {
        let walkthroughJSON = {
            flowData: walkthroughFlowData
        };
        window.sessionStorage.setItem("builder.previewFlowData", JSON.stringify(walkthroughJSON));
        if (window.location.href.replace(window.location.origin, "").split('#')[0] == firstStepUrl.split('#')[0] ) {
            window.location.href = window.location.origin + firstStepUrl;
            window.setTimeout( () => {
                window.location.reload();
            }, 100 );
        } else {
            window.location.href = window.location.origin + firstStepUrl;
        }
    }

    getBoundMethodsRef() {
        // organised 'this' bound eventHandlers to maintain method reference
        return {
            escapeKeyHandler: this.escapePreview.bind(this)
        }
    }

    handleOngoingPreview(walkthroughConf) {
        this.onGoingPreviewData = JSON.parse(window.sessionStorage.getItem("builder.previewFlowData"));
        this.setRenderingSDKInstance(walkthroughConf);
        this.renderingSDK.start();
        this.setPreviewListenters();
        this.createInfoElement();
    }

    setRenderingSDKInstance(walkthroughConf) {
        this.renderingSDK = new WalkthroughWrapper();
        this.setBundleConf(walkthroughConf);
        let wrapperDataFormat = {
            pid: -1,
            materialid: 'walkthroughbuilderpreview',
            data: {}
        }
        wrapperDataFormat.data["walkthroughbuilderpreview"] = this.onGoingPreviewData.flowData;
        this.renderingSDK.init(wrapperDataFormat, this.overWriteFunc);
    }

    setBundleConf(walkthroughConf) {
        if (walkthroughConf.isDap) {
            this.renderingSDK.setworkspaceconf(walkthroughConf.workspaceConf);
        }
    }
    onMetricsReceived(metric) {
        this.lastReceivedMetric = metric;
        if (metric.statuscode == 3 || metric.statuscode == 4 || metric.statuscode == 5 || (metric.statuscode == 2 && metric.stepnumber == this.onGoingPreviewData.flowData.templates.length)) {
            this.endPreview();
        }
    }

    setPreviewListenters() {
        // escape key listener
        this.clearListenersCallback = this.registerEscapeListenerAcrossFrames(this.eventHandlers.escapeKeyHandler);
        // document.addEventListener("keydown", this.eventHandlers.escapeKeyHandler, true);
        InProduct_CrossOriginMessenger.instance.sendMsgToAllChild('addEventListener' ,{},"walkthroughpreview");
    }

    createInfoElement() {
        this.closedContainer.initialize();
        let infoElementConf = {
            tagName: "div",
            id: "mics-previewModeInfo",
            htmlContent: this.getInfoHtmlContent()
        }
        this.elementsRef.info = this.Util.createHtmlElement(infoElementConf);
        this.closedContainer.getShadowRoot().appendChild(this.elementsRef.info);
        let infoStyleConf = {
            tagName: "style",
            id: "walkthroughInfoStyle",
            htmlContent: this.getInfoStyle()
        };
        this.elementsRef.infoStyle = this.Util.createHtmlElement(infoStyleConf);
        this.closedContainer.getShadowRoot().appendChild(this.elementsRef.infoStyle);
    }

    getInfoHtmlContent() {
        return `<div><span> Click <span class="highlightedText" >Esc</span> to close preview </span></div>`;
    }

    getInfoStyle() {
        return `#mics-previewModeInfo{
                    width: fit-content;
                    text-align: center;
                    z-index: 9999999999999999999999999999999;
                    gap: 0.2vw;
                    padding: 2vw 2vw;
                    padding: 0.2vw 1vw;
                    position: fixed;
                    user-select: none;
                    bottom: 0;
                    inset: auto 0px 5vw;
                    height: 40px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    background-color: #232935;
                    border-radius: 6px;
                    box-shadow: #00000040 0 0 12px;
                    opacity: .95;
                    color: #ffffffb3;
                    top: 90%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    pointer-events: none;
                }

                #mics-previewModeInfo.hide{
                    inset: auto 0 -5vw;
                }
                
                #mics-previewModeInfo>div>span>span.highlightedText{
                    color: #dfdfdf;
                    font-weight: bold;
                }`;
    }

    escapePreview(event) {
        if (event.key == "Escape") {
            this.Util.preventEventBehaviours(event);
            InProduct_CrossOriginMessenger.instance.sendMsgToAllChild("removeEventListener" , {} ,"walkthroughpreview");
            this.renderingSDK.endTour();
            this.endPreview();
        }
    }

    endPreview() {
        this.removePreviewListeners();
        this.clearPreviewInfo();
        this.onEndPreviewCallback(this.lastReceivedMetric);
    }

    removePreviewListeners() {
        if (this.clearListenersCallback && typeof this.clearListenersCallback.cleanup === 'function') {
            this.clearListenersCallback.cleanup();
        }
        this.clearListenersCallback = null;
    }

    clearPreviewInfo() {
        this.elementsRef.info.classList.add("hide");
        this.elementsRef.info.remove();
        this.elementsRef.infoStyle.remove();
        this.closedContainer.destroy();
    }

    registerEscapeListenerAcrossFrames(callback) {
        if (typeof callback !== 'function') {
            throw new TypeError('Callback must be a function');
        }

        const listeners = new Map(); // Store iframe -> handler mapping
        let mutationObserver = null;

        // Create the escape key handler
        const escapeHandler = (event) => {
            if (event.key === 'Escape' || event.key === 'Esc' || event.keyCode === 27) {
                callback(event);
            }
        };

        // Safely check if an iframe is same-origin
        const isSameOrigin = (iframe) => {
            try {
                // Attempt to access contentDocument - this will throw if cross-origin
                const doc = iframe.contentDocument || iframe.contentWindow?.document;
                return doc !== null && doc !== undefined;
            } catch (e) {
                // Cross-origin access denied
                return false;
            }
        };

        // Register listener on a specific target (document or iframe document)
        const registerListener = (target, iframe = null) => {
            if (!target) return;

            const handler = (event) => escapeHandler(event);
            target.addEventListener('keydown', handler, true);
            
            if (iframe) {
                listeners.set(iframe, { target, handler });
            } else {
                // Store main document listener
                listeners.set('_mainDocument', { target, handler });
            }
        };

        // Remove listener from a specific target
        const removeListener = (key) => {
            const listenerInfo = listeners.get(key);
            if (listenerInfo) {
                listenerInfo.target.removeEventListener('keydown', listenerInfo.handler, true);
                listeners.delete(key);
            }
        };

        // Process an iframe element
        const processIframe = (iframe) => {
            // Skip if already registered
            if (listeners.has(iframe)) return;

            if (isSameOrigin(iframe)) {
                try {
                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    if (iframeDoc && iframeDoc.readyState === 'complete') {
                        registerListener(iframeDoc, iframe);
                    } else {
                        // Wait for iframe to load
                        iframe.addEventListener('load', () => {
                            if (isSameOrigin(iframe)) {
                                const doc = iframe.contentDocument || iframe.contentWindow.document;
                                registerListener(doc, iframe);
                            }
                        }, { once: true });
                    }
                } catch (e) {
                    // Silently ignore cross-origin or other errors
                }
            }
        };

        // Initial registration on main document
        registerListener(document);

        // Register on all existing same-origin iframes
        const existingIframes = document.querySelectorAll('iframe');
        existingIframes.forEach(processIframe);

        // Set up MutationObserver to watch for dynamically added iframes
        mutationObserver = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        // Check if the node itself is an iframe
                        if (node.tagName === 'IFRAME') {
                            processIframe(node);
                        }
                        // Check if the node contains iframes
                        if (node.querySelectorAll) {
                            const iframes = node.querySelectorAll('iframe');
                            iframes.forEach(processIframe);
                        }
                    }
                });

                // Clean up listeners for removed iframes
                mutation.removedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE && node.tagName === 'IFRAME') {
                        removeListener(node);
                    }
                });
            });
        });

        // Start observing
        mutationObserver.observe(document.body, {
            childList: true,
            subtree: true
        });

        // Return cleanup object
        return {
            cleanup: () => {
                // Stop observing mutations
                if (mutationObserver) {
                    mutationObserver.disconnect();
                    mutationObserver = null;
                }

                // Remove all registered listeners
                listeners.forEach((listenerInfo, key) => {
                    listenerInfo.target.removeEventListener('keydown', listenerInfo.handler, true);
                });
                listeners.clear();
            }
        };
    }

}// $Id$
class CssSelector {

    constructor(onTargetSelected) {
        this.targetElementData = {
            element: null,
            dimensions: {},
            selector: ""
        };
        this.onTargetSelectedCallback = onTargetSelected;
        this.selectorConf = null;
        this.elementsRef = {
            highlighter: null,
            cursorStyleTag: null,
            crossoriginwarning: null,
            info: null,
            infoStyle: null
        };
        this.eventHandlers = this.getBoundMethodsRef();
        this.Util = WalkthroughBuilderSDKUtility;
        this.cqs = new CustomQuerySelector();
        this.iframeHandle = new IframeContentSelector(this.onEventsFromIframe.bind(this));
        this.closedContainer = new InproductContainer('walkthrough-selector-info');
        this.cssSelectorElementConf = { showInfo: true };
        this.selectorFormat = undefined;
    }

    getBoundMethodsRef() {
        // organised 'this' bound eventHandlers to maintain method reference
        return {
            fetchTargetElement: this.fetchTargetElement.bind(this),
            escapeKeyHandler: this.escapeKeyHandler.bind(this),
            updateTargetSelector: this.updateTargetSelector.bind(this),
            handleMouseout:this.handleMouseout.bind(this)
            // onMouseenterIframe: this.onMouseenterIframe.bind(this)
        }
    }

    startSelectorMode(cssSelectorElementConf) {
        this.targetElementData.selector = "";
        this.closedContainer.initialize();
        this.createHighlighterElement();
        this.changeCursorStyle();
        this.iframeHandle.startIframeSelector();
        this.setSelectorEventListeners();
        cssSelectorElementConf ?  this.cssSelectorElementConf = cssSelectorElementConf : "";
        this.cssSelectorElementConf.showInfo ? this.createInfoElement() : "";
        InProduct_CrossOriginMessenger.instance.sendMsgToAllChild('selectorModeOn' ,{ selectorConf :this.selectorConf, selectorFormat: this.selectorFormat},"walkthroughbuilder")
    }

    createHighlighterElement() {
        let highlighterConf = {
            tagName: "div",
            id: "walkthroughHighlighterElement"
        }
        this.elementsRef.highlighter = this.Util.createHtmlElement(highlighterConf);
        this.closedContainer.getShadowRoot().appendChild(this.elementsRef.highlighter);
        let styleObj = {
            "position": "fixed",
            "border": "1px solid #6ffff8",
            "backgroundColor": "#6fdddb8c",
            "pointer-events": "none",
            "z-index": "999999999"
        };
        this.Util.setElementStyle(this.elementsRef.highlighter, styleObj);
        this.createCrossOriginWarningElement();
    }

    createCrossOriginWarningElement() {
        let elementConf = {
            tagName: "div",
            id: "walkthroughCrossOriginElement"
        }
        this.elementsRef.crossoriginwarning = this.Util.createHtmlElement(elementConf);
        this.elementsRef.crossoriginwarning.innerHTML = `<div style="display: flex"><svg xmlns="" height="1.2vw" viewBox="0 0 24 24" width="1.5vw" fill="#B89230"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"></path></svg></div> <div style="display: flex; align-items: center;">We're unable to add a step here because this section is from another source!</div>`;
        this.elementsRef.highlighter.appendChild(this.elementsRef.crossoriginwarning);
        let styleObj = {
            "display": "none",
            "position": "relative",
            "top": "50%",
            "left": "50%",
            "width": "fit-content",
            "transform": "translate(-50%, -50%)",
            "background-color": "rgb(255, 243, 205)",
            "pointer-events": "none",
            "color": "rgb(160 135 60)",
            "padding": "0.57em 0.75em",
            "border-radius": "0.2vw",
            "font-size": "0.85vw",
            "box-shadow": "rgb(68 68 68 / 20%) 0px 2px 8px 0px"
        };
        this.Util.setElementStyle(this.elementsRef.crossoriginwarning, styleObj);
    }

    changeCursorStyle() {
        let styleConf = {
            tagName: "style",
            id: "walkthroughCursorStyle",
            htmlContent: '* { cursor: crosshair !important; }'
        }
        this.elementsRef.cursorStyleTag = this.Util.createHtmlElement(styleConf);
        document.documentElement.appendChild(this.elementsRef.cursorStyleTag);
    }

    onEventsFromIframe(params) {
        switch (params.action) {
            case 'fetchedTarget':
                this.fetchTargetElement(params.event);
                break;
            case 'updateTarget':
                this.updateTargetSelector(params.event);
                break;
            case 'escape':
                this.escapeKeyHandler(params.event);
                break;
            default:
                break;
        }
    }

    setSelectorEventListeners() {
        window.focus();
        window.addEventListener("mousemove", this.eventHandlers.fetchTargetElement, true);
        document.addEventListener('keydown', this.eventHandlers.escapeKeyHandler, true);
        document.addEventListener("click", this.eventHandlers.updateTargetSelector, true);
        document.addEventListener('mousedown', this.preventEventBehaviours, true);
        document.addEventListener('mouseup', this.preventEventBehaviours, true);
        document.addEventListener("mouseout",this.eventHandlers.handleMouseout,true);
    }

    createInfoElement() {
        let infoElementConf = {
            tagName: "div",
            id: "selectorModeInfo",
            htmlContent: this.getInfoHtmlContent()
        }
        this.elementsRef.info = this.Util.createHtmlElement(infoElementConf);
        this.closedContainer.getShadowRoot().appendChild(this.elementsRef.info);
        let infoStyleConf = {
            tagName: "style",
            id: "walkthroughInfoStyle",
            htmlContent: this.getInfoStyle()
        }
        this.elementsRef.infoStyle = this.Util.createHtmlElement(infoStyleConf);
        this.closedContainer.getShadowRoot().appendChild(this.elementsRef.infoStyle);
    }

    getInfoHtmlContent() {
        return `<span class="text"> Select an element to add a tooltip, or press 
                    <span style="font-weight: bold;">Esc</span> to go back
                </span>`
    }

    getInfoStyle() {
        return `#selectorModeInfo{
                    width: max-content;
                    height: 2.8vw;
                    min-width: 8vw;
                    pointer-events: none;
                    z-index: 999999999;
                    padding: 0 1.5vw;
                    position: fixed;
                    inset: auto 0 2.5vw;
                    margin-left: auto;
                    margin-right: auto;
                    justify-content: center;
                    display: flex;
                    align-items: center;
                    background-color: #232935eb;
                    border-radius: 0.25vw;
                    box-shadow: rgba(0, 0, 0, 0.3) 0px 0px 12px;
                }

                #selectorModeInfo.hide{
                    inset: auto 0 -5vw;
                }
                
                #selectorModeInfo>.text{
                    font-size: 0.9vw;
                    letter-spacing: 0.035em;
                    color: rgba(255, 255, 255, 0.9);
                }`;
    }

    fetchTargetElement(event) {
        this.elementsRef.highlighter.style.display = "block";
        this.preventEventBehaviours(event);
        let doc = event.view && event.view.document ? event.view.document : document;
        let element = this.cqs.getElementFromPoint({
            x: event.clientX,
            y: event.clientY
        }, doc);
         if(this.iframeHandle.crossOriginWarningShowedIframe ){
            var rect = this.iframeHandle.crossOriginWarningShowedIframe.getBoundingClientRect()
            if (event.clientX >= rect.left && event.clientX <= rect.right && event.clientY >= rect.top && event.clientY <= rect.bottom){
                return;
            }
        }
        if (element && element != this.targetElementData.element && element.tagName != 'IFRAME') {
            this.targetElementData.element = element;
            this.iframeHandle.crossOriginWarningShowedIframe ? this.iframeHandle.crossOriginWarningShowedIframe.style.pointerEvents = "auto" : "";
            this.iframeHandle.crossOriginWarningShowedIframe = null;
            this.hidecrossoriginwarning();
            this.highlightTargetElement();

        }
        if(element && element.tagName.toLowerCase() == 'iframe'){
            let isCrossOrigin = false;
            try {
                isCrossOrigin = element.src && new URL(element.src).origin !== window.location.origin;
            } catch(e) {
                isCrossOrigin = true;
            }
            if(isCrossOrigin && InProduct_CrossOriginMessenger.instance.registeredIframeRef.includes(element)){
                this.removeCrossOriginWhileSelector();
            }
            else if(isCrossOrigin){
                this.targetElementData.element = element;
                element.style.pointerEvents = "none";
                this.iframeHandle.crossOriginWarningShowedIframe = element;
                this.highlightTargetElement();
                this.showcrossoriginwarning();
            }
        }
    }
    removeCrossOriginWhileSelector(){
        this.hidecrossoriginwarning();
        this.hideSelectorElements();
        this.iframeHandle.crossOriginWarningShowedIframe ? this.iframeHandle.crossOriginWarningShowedIframe.style.pointerEvents = "auto" : "";
        this.iframeHandle.crossOriginWarningShowedIframe = null;
    }
    showcrossoriginwarning(element) {
        this.elementsRef.crossoriginwarning.style.display = "flex";
    }
    hidecrossoriginwarning() {
        this.elementsRef.crossoriginwarning.style.display = "none";
    }
    highlightTargetElement() {
        this.targetElementData.dimensions = this.cqs.getElementDimensions(this.targetElementData.element);
        this.setHighlighterPosition(this.targetElementData.dimensions);
    }

    setHighlighterPosition(boundingRect) {
        let styleObj = {
            "top": boundingRect.top + "px",
            "left": boundingRect.left + "px",
            "height": boundingRect.height + "px",
            "width": boundingRect.width + "px"
        }
        this.Util.setElementStyle(this.elementsRef.highlighter, styleObj)
    }

    highlightIframeTarget(element) {
        if (element != this.targetElementData.element) {
            this.elementsRef.highlighter.style.display = "block";
            this.targetElementData.element = element;
            this.targetElementData.dimensions = this.cqs.getElementDimensions(element);
            this.setHighlighterPosition(this.targetElementData.dimensions);
        }
    }
    escapeKeyHandler(event) {
        this.preventEventBehaviours(event);
        if (event.key == "Escape") {
            this.endSelectorMode(event);
        }
    }
    endSelectorMode(event) {
        WalkthroughBuilderSDK.instance.currentMode = null;
        event ? this.preventEventBehaviours(event) : "";
        this.clearSelectorEventListeners();
        InProduct_CrossOriginMessenger.instance.sendMsgToAllChild("selectorModeOff",{},"walkthroughbuilder");
        delete this.targetElementData.element;
        (this.onTargetSelectedCallback) ? this.onTargetSelectedCallback(this.targetElementData) : '';
        this.clearSelectorElements();
        this.iframeHandle.clearIframeHandlers();
        this.iframeHandle.crossOriginWarningShowedIframe ? this.iframeHandle.crossOriginWarningShowedIframe.style.pointerEvents = "auto" : "";
        this.iframeHandle.crossOriginWarningShowedIframe = null;
    }
    crossOriginEndSelectorMode(){
        this.clearSelectorEventListeners();
        this.clearSelectorElements();
        this.iframeHandle.clearIframeHandlers();
    }
    preventEventBehaviours(event) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
    }

    clearSelectorEventListeners() {
        window.removeEventListener("mousemove", this.eventHandlers.fetchTargetElement, true);
        document.removeEventListener('keydown', this.eventHandlers.escapeKeyHandler, true);
        document.removeEventListener("click", this.eventHandlers.updateTargetSelector, true);
        document.removeEventListener('mousedown', this.preventEventBehaviours, true);
        document.removeEventListener('mouseup', this.preventEventBehaviours, true);
        document.removeEventListener("mouseout",this.eventHandlers.handleMouseout,true);
    }

    clearSelectorElements() {
        this.elementsRef.highlighter.remove();
        this.elementsRef.cursorStyleTag.remove();
        this.clearInfoElements();
        this.closedContainer.destroy();
    }
    clearInfoElements(){
        if(this.cssSelectorElementConf.showInfo){
            this.elementsRef.info.classList.add("hide");
            this.elementsRef.info.remove();
            this.elementsRef.infoStyle.remove();
        }
    }

    setSelectorConf(conf) {
        this.selectorConf = (conf) ? conf : this.selectorConf;
    }

    getSelectorConf() {
        let selectorConf = {
            id: true,
            classname: true,
            dataattribute: false
        };
        return (this.selectorConf && Object.keys(this.selectorConf).length != 0) ? this.selectorConf : selectorConf;
    }

    updateTargetSelector(event) {
        this.preventEventBehaviours(event);
        if (this.targetElementData.element) {
            this.targetElementData.selector = this.cqs.constructSelector(this.targetElementData.element, this.getSelectorConf(), this.selectorFormat);
            this.endSelectorMode(event);
        }
    }
    handleMouseout(event){
        this.hideSelectorElements();
    }
    hideSelectorElements(){
        this.elementsRef.highlighter.style.display = "none";
    }
    setOnSelectedCallback(onTargetSelected) {
        this.onTargetSelectedCallback = onTargetSelected;
    }

    setSelectorFormat( selectorFormat ) {
        this.selectorFormat = selectorFormat;
    }

}// $Id$
class DOMObserver {

    constructor(onObservedDomChange) {
        this.onObservedDomChange = onObservedDomChange;
        this.activeTargetElement = null;
        this.targetElementSelector = '';
        this.initialDimensions = { top: 0, left: 0, height: 0, width: 0, x: 0, y: 0 };
        this.domObserver = {
            mutationObserver: null,
            resizeObserver: null,
            positionCheckIntervalID: ''
        };
        this.Util = WalkthroughBuilderSDKUtility;
    }

    setTargetElement(element) {
        (this.activeTargetElement) ?
            this.destroyDOMObservers() : '';
        this.activeTargetElement = element;
        this.Util.scrollToTarget(this.activeTargetElement);
        this.observeDOMElement();
    }

    observeDOMElement() {
        this.setMutationObserver();
        this.setResizeObserver();
        this.checkPositionOnInterval();
    }

    setMutationObserver() {
        let timeoutId;
        this.domObserver.mutationObserver = new MutationObserver(() => {
            this.initialDimensions = this.getElementDimensions(this.activeTargetElement);
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => { this.onObservedDomChange(this.initialDimensions) }, 10)
        });
        this.domObserver.mutationObserver.observe(this.activeTargetElement, {
            childList: true,
            subtree: true,
            attributes: true
        });
    }

    setResizeObserver() {
        let timeoutId;
        this.domObserver.resizeObserver = new ResizeObserver(() => {
            this.initialDimensions = this.getElementDimensions(this.activeTargetElement);
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => { this.onObservedDomChange(this.initialDimensions) }, 10)
        });
        this.domObserver.resizeObserver.observe(this.activeTargetElement);
    }

    checkPositionOnInterval() {
        let self = this;
        this.initialDimensions = self.getElementDimensions(self.activeTargetElement);
        let currentDimensions, timeoutId;

        window.clearInterval(self.domObserver.positionCheckIntervalID);
        self.onObservedDomChange(self.initialDimensions);
        self.domObserver.positionCheckIntervalID = window.setInterval(() => {
            currentDimensions = self.getElementDimensions(self.activeTargetElement);
            if (!self.activeTargetElement.isConnected || self.initialDimensions.top !== currentDimensions.top ||
                self.initialDimensions.left !== currentDimensions.left) {
                self.initialDimensions = currentDimensions;
                clearTimeout(timeoutId);
                timeoutId = setTimeout(() => { this.onObservedDomChange(this.initialDimensions) }, 10)
            }
        }, 1000);
    }

    getElementDimensions(element) {
        try {
            return this.Util.getElementDimensions(element);
        }
        catch (err) { };
        return { top: 0, left: 0, height: 0, width: 0, x: 0, y: 0 };
    }

    destroyDOMObservers() {
        if (this.activeTargetElement) {
            this.domObserver.mutationObserver.disconnect();
            this.domObserver.resizeObserver.disconnect();
            window.clearInterval(this.domObserver.positionCheckIntervalID);
        }
    }

    getCurrentTarget() {
        return this.activeTargetElement;
    }

}
// $Id$
class Interaction {

    constructor(onEndInteraction) {
        this.onEndInteractionCallback = onEndInteraction;
        this.targetElementData = {};
        this.elementsRef = {
            endInteractionBtn: null,
            endInteractionBtnStyle: null,
            backdropRoot: null,
            highlighterBox: null
        };
        this.windowDimensions = {
            height: 0,
            width: 0
        };
        this.enableClickthrough = false;
        this.backdropBoxes = ["topbox", "bottombox", "rightbox", "leftbox"]
        this.eventHandlers = this.getBoundMethodsRef();
        this.domObserver = new DOMObserver(this.eventHandlers.repositionInteractArea);
        this.Util = WalkthroughBuilderSDKUtility;
        this.closedContainer = new InproductContainer('walkthrough-interaction-info');
    }

    getBoundMethodsRef() {
        return {
            endInteractionMode: this.endInteractionMode.bind(this),
            repositionInteractArea: this.repositionInteractArea.bind(this)
        };
    }

    startInteractionMode(targetElementData, backdropConfig, highlighterConfig) {
        this.targetElementData = JSON.parse(JSON.stringify(targetElementData));
        this.targetElementData.element = this.Util.getElement(this.targetElementData.selector);
        this.calculateWindowDimension();
        this.closedContainer.initialize();
        this.createBackdropRoot();
        this.drawBackdrop(backdropConfig);
        (highlighterConfig.type != "None") ? this.drawHighlighterBox(highlighterConfig) : '';
        this.createEndInteractionBtn();
        this.setInteractionEventListeners();
    }

    calculateWindowDimension() {
        let html = document.documentElement;
        this.windowDimensions.height = Math.max(document.body.scrollHeight, document.body.offsetHeight, html.clientHeight, html.scrollHeight, html.offsetHeight);
        let windowInnnerWidth = window.innerWidth || document.documentElement.clientWidth || document.body.clientWidth;
        let scrollbarWidth = windowInnnerWidth - document.documentElement.clientWidth;
        this.windowDimensions.width = windowInnnerWidth - scrollbarWidth;
    }

    createBackdropRoot() {
        let backdropRootConf = {
            tagName: "div",
            id: "",
            className: "walkthroughBackdropRoot"
        };
        this.elementsRef.backdropRoot = this.Util.createHtmlElement(backdropRootConf);
        this.closedContainer.getShadowRoot().appendChild(this.elementsRef.backdropRoot);
        this.elementsRef.backdropRoot.style.position = "fixed";
        this.elementsRef.backdropRoot.style.zIndex = "10000000000000000000";
    }

    drawBackdrop(backdropConfig) {
        let backdropElementConf = { tagName: "div", className: "", id: "" };
        let backdropStyle = { position: "fixed" };
        backdropStyle.backgroundColor = (backdropConfig.type == "Overlay") ? "#01010171" : "transparent";
        backdropStyle.pointerEvents = (backdropConfig.hasClickthrough) ? "none" : "all";
        for (let i = 0; i < this.backdropBoxes.length; i++) {
            backdropElementConf.className = "backdrop" + this.backdropBoxes[i];
            let backdropElement = this.Util.createHtmlElement(backdropElementConf);
            this.elementsRef.backdropRoot.appendChild(backdropElement);
            this.Util.setElementStyle(backdropElement, backdropStyle);
        }
        this.positionBackdrop();
    }

    positionBackdrop() {
        let targetElementDimensions = this.targetElementData.dimensions;
        let backdropDimensions = {
            leftbox: {
                top: 0,
                left: 0,
                height: this.windowDimensions.height + 'px',
                width: targetElementDimensions.left + 'px'
            },
            rightbox: {
                top: 0,
                right: 0,
                height: this.windowDimensions.height + 'px',
                width: this.windowDimensions.width - targetElementDimensions.left - targetElementDimensions.width + 'px'
            },
            bottombox: {
                top: targetElementDimensions.top + targetElementDimensions.height + 'px',
                left: targetElementDimensions.left + 'px',
                height: this.windowDimensions.height - targetElementDimensions.top - targetElementDimensions.height + 'px',
                width: targetElementDimensions.width + 'px'
            },
            topbox: {
                top: 0,
                left: targetElementDimensions.left + 'px',
                height: targetElementDimensions.top > 0 ? targetElementDimensions.top + 'px' : '0px',
                width: targetElementDimensions.width + 'px'
            }
        };
        for (let i = 0; i < this.backdropBoxes.length; i++) {
            let backdrop = this.elementsRef.backdropRoot.querySelector(".backdrop" + this.backdropBoxes[i]);
            this.Util.setElementStyle(backdrop, backdropDimensions[this.backdropBoxes[i]]);
        }
    }

    drawHighlighterBox(highlighterConfig) {
        let highlighterBoxConf = { tagName: "div", className: "highlighterBox", id: "" };
        this.elementsRef.highlighterBox = this.Util.createHtmlElement(highlighterBoxConf);
        this.elementsRef.highlighterBox.style.outline = highlighterConfig.bordercolor + " solid " + highlighterConfig.borderwidth + "px";
        this.elementsRef.highlighterBox.style.position = "fixed";
        this.elementsRef.highlighterBox.style.pointerEvents = "none";
        let borderradius = highlighterConfig.borderradius.trim().split(" ");
        this.elementsRef.highlighterBox.style.borderRadius = (borderradius[0] || "0") + "px " + (borderradius[1] || "0")
            + "px " + (borderradius[2] || "0") + "px " + (borderradius[3] || "0") + "px";
        this.elementsRef.backdropRoot.appendChild(this.elementsRef.highlighterBox);
        this.positionHighlighterBox();
    }

    positionHighlighterBox() {
        let targetElementDimensions = this.targetElementData.dimensions;
        let highlighterBoxDimension = {
            top: targetElementDimensions.top + "px",
            left: targetElementDimensions.left + "px",
            height: targetElementDimensions.height + "px",
            width: targetElementDimensions.width + "px"
        };
        this.Util.setElementStyle(this.elementsRef.highlighterBox, highlighterBoxDimension);
    }

    createEndInteractionBtn() {
        let btnConf = {
            tagName: "div",
            id: "walkthroughEndInteractionBtn",
            htmlContent: this.getEndInteractionBtnHtml()
        }
        this.elementsRef.endInteractionBtn = this.Util.createHtmlElement(btnConf);
        this.elementsRef.backdropRoot.appendChild(this.elementsRef.endInteractionBtn);
        let btnStyleConf = {
            tagName: "style",
            id: "walkthrougEndInteractionBtnStyle",
            htmlContent: this.getEndInteractionBtnStyle()
        };
        this.elementsRef.endInteractionBtnStyle = this.Util.createHtmlElement(btnStyleConf);
        this.elementsRef.backdropRoot.appendChild(this.elementsRef.endInteractionBtnStyle);
    }

    getEndInteractionBtnHtml() {
        return `<div id="borderanimation"></div>
                <div id="text">Click here after interaction.</div>`;
    }

    getEndInteractionBtnStyle() {
        return `#walkthroughEndInteractionBtn {
                  height: max-content;
                  width: max-content;
                  text-align: center;
                  cursor: pointer;
                  z-index: 9999999999999;
                  padding: 2px;
                  position: fixed;
                  inset: auto 0 5vw;
                  margin-left: auto;
                  margin-right: auto;
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  background: #00232e;
                  border-radius: 5px;
                  box-shadow: #0000009e -1px 7px 12px;
                  overflow: hidden;
                  transition: 0.2s ease-in-out;
                }

                #walkthroughEndInteractionBtn.hide {
                  inset: auto 0px -5vw;
                }

                #walkthroughEndInteractionBtn>#text {
                  width: max-content;
                  max-width: 30vw;
                  min-width: 8vw;
                  height: 2.9vw;
                  background-color: #00232e;
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  border-radius: 0.2vw;
                  padding: 0 1.75vw;
                  font-size: 0.9vw;
                  letter-spacing: 0.035em;
                  color: #ffffffef;
                }

                #walkthroughEndInteractionBtn>#borderanimation {
                  animation: rotate 2s linear infinite;
                  background: linear-gradient(90deg, rgba(0, 0, 0, 0) 23%, rgb(0 238 222) 100%);
                  width: 40vw;
                  height: 40vw;
                  position: absolute;
                  z-index: -1;
                }

                @keyframes rotate {
                  0% {
                    transform: rotate(1turn);
                  }
                }`
    }

    setInteractionEventListeners() {
        this.elementsRef.endInteractionBtn.addEventListener("click", this.eventHandlers.endInteractionMode);
        window.addEventListener("resize", this.eventHandlers.repositionInteractArea);
    }

    repositionInteractArea() {
        this.calculateWindowDimension();
        this.positionBackdrop();
        (this.elementsRef.highlighterBox) ? this.positionHighlighterBox() : null;
    }

    endInteractionMode() {
        this.elementsRef.endInteractionBtn.removeEventListener("click", this.eventHandlers.endInteractionMode);
        this.domObserver.destroyDOMObservers();
        window.removeEventListener("resize", this.eventHandlers.repositionInteractArea);
        this.clearInteractionContents();
        this.onEndInteractionCallback();
    }

    clearInteractionContents() {
        this.elementsRef.backdropRoot.remove();
        this.closedContainer.destroy();
    }

}// $Id$

class BuilderSDKMessenger {

    constructor(builderSDKRef) {
        this.builderSDK = builderSDKRef;
        this.receiverWindow = null;
        this.targetOrigin = '';
        this.setMessageListener();
    }

    setMessageListener() {
        this.messageListener = (event) => {
            if ( event.origin == this.targetOrigin && event.data.targetName === "walkthroughBuilderSDK") {
                this.messageHandler(event.data.action, event.data.payload);
            }
        };
        window.addEventListener("message", this.messageListener);
    }

    messageHandler(action, payload) {
        action = (action) ? action : '';
        switch (action) {
            case "iframeLoaded":
                this.builderSDK.onIframeLoaded();
                break;
            case 'initBuilder':
                this.builderSDK.createBuilder(payload.micsWalkthroughConfig);
                break;
            case 'cssSelectorMode':
                this.builderSDK.startCssSelectorMode(payload.selectorConf, payload.selectorFormat);
                break;
            case 'validateNSetDomTarget':
                this.builderSDK.stopDomObserversForPreviousStep();		                
	            this.builderSDK.setChildElement(payload.selector);		                
	            this.builderSDK.validateNSetTargetElement(this.builderSDK.targetElementData.selector, payload.elementMeta);
                break;
            case 'getCurrentUrl':
                this.builderSDK.sendCurrentUrlToIframe();
                break;
            case 'getNewCssSelector':
                this.builderSDK.getNewCssSelector(payload.selector, payload.selectorConf, payload.selectorFormat, payload.elementMeta);
                break;
            case 'previewMode':
                this.builderSDK.startBuilderPreview(payload.flowStartingUrl, payload.walkthroughFlowData);
                break;
            case "navigationMode":
                this.builderSDK.startNavigationMode();
                break;
            case "setDOMObserverTarget":
                this.builderSDK.setChildElement(payload.selector);
                this.builderSDK.validateNSetTargetElement(payload.selector, payload.elementMeta);
                break;
            case "triggerTarget":
                this.builderSDK.triggerTargetElement();
                break;
            case "interactiveMode":
                this.builderSDK.startInteractiveMode(payload.backdropConfig, payload.highlighterConfig);
                break;
            case "exitBuilder":
                this.builderSDK.removeBuilder();
                break;
            case "preview":
                this.builderSDK.startPreviewFlow(payload.micsWalkthroughConfig);
                break;
            case "verify":
                this.builderSDK.startVerifyFlow(payload.micsWalkthroughConfig);
                break;
            case "edit":
                this.builderSDK.startEditingFlow(payload.micsWalkthroughConfig);
                break;
            case "closeTab":
                this.builderSDK.closeTab();
            case "onWalkthroughSaved":
                this.updateWalkthroughSavedState();
        }
    }

    updateSDKReadyState() {
        window.postMessage({ targetName: "extensionContentScript" }, "*");
    }

    updateWalkthroughSavedState() {
        window.opener.postMessage({ WalkthroughCallback: true, status: 'success', type: 'save' }, "*");
    }

    initializeIframeCommunication(iframeWindow, frameOrigin) {
        this.receiverWindow = iframeWindow;
        this.targetOrigin = frameOrigin ? frameOrigin : "*";
    }

    messageToBuilderIframe(action, payload) {
        let msgData = {
            targetName: "walkthroughBuilderIframe",
            action: action,
            source:"inproductsdk",
            origin:"inproduct_childsdk",
            mode:"walkthroughbuilder",
            data: payload,
            payload: payload
        };
        this.receiverWindow.postMessage(msgData, this.targetOrigin);
    }

    removeMessageListener() {
        window.removeEventListener("message", this.messageListener);
    }

}
/*$Id$*/

class CustomQuerySelector {

    constructor() {
        this.context = null;
        this.selectorSequence = [];
        this.contextElements = [];
        this.setDefaults();
    }

    setDefaults() {
        this.context = document;
    }

    getElementFromPoint(position, context) {
        this.context = context || this.context;
        let currElement = this.context.elementFromPoint(position.x, position.y);
        if (currElement && currElement.shadowRoot && (this.context != currElement.shadowRoot)) {
            this.context = currElement.shadowRoot;
            return this.getElementFromPoint(position);
        }
        this.context = document;
        return currElement;
    }

    getElementDimensions(element) {
        const elementRect = element.getBoundingClientRect();
        const dimensions = {
            x: elementRect.x,
            y: elementRect.y,
            top: elementRect.top,
            left: elementRect.left,
            width: elementRect.width,
            height: elementRect.height
        };
        let currentElement = element;
        while (currentElement.ownerDocument.defaultView.frameElement) {
            const frame = currentElement.ownerDocument.defaultView.frameElement;
            const frameRect = frame.getBoundingClientRect();
            const frameStyle = getComputedStyle(frame);
            dimensions.top += frameRect.top + parseFloat(frameStyle.borderTopWidth || 0);
            dimensions.left += frameRect.left + parseFloat(frameStyle.borderLeftWidth || 0);
            dimensions.y += frameRect.y + parseFloat(frameStyle.borderTopWidth || 0);
            dimensions.x += frameRect.x + parseFloat(frameStyle.borderLeftWidth || 0);
            currentElement = frame;
        };
        return dimensions;
    }

    getIframeDimensionForChild(iframeRef, dimensions) {
        const rect = this.getElementDimensions(iframeRef);
        const style = getComputedStyle(iframeRef);
        dimensions.x += rect.x + parseFloat(style.borderLeftWidth || 0);
        dimensions.y += rect.y + parseFloat(style.borderTopWidth || 0);
        dimensions.left += rect.left + parseFloat(style.borderLeftWidth || 0);
        dimensions.top += rect.top + parseFloat(style.borderTopWidth || 0);
        return dimensions;
    }

    parseStringToArray(selectorStr) {
        return selectorStr.split("|");
    }

    parseArrayToString(selectorArr) {
        return selectorArr.join(" ");
    }

    constructSelector(element, selectorConf, selectorFormat) {
        let selectorList = [];
        let selector = '';
        if (document.contains(element)) {
            selector = this.getUniqueCssSelector(element, selectorConf, document, selectorFormat);
        }
        else if (element.ownerDocument != document) {
            let currentElement = element;
            while (currentElement.ownerDocument !== document) {
                const iframeElement = currentElement.ownerDocument.defaultView.frameElement;
                selectorList.unshift(this.getUniqueCssSelector(currentElement, selectorConf, currentElement.ownerDocument, selectorFormat));
                selectorList.unshift('|iframe|');
                currentElement = iframeElement;
            }
            selectorList.unshift(this.getUniqueCssSelector(currentElement, selectorConf, currentElement.ownerDocument, selectorFormat));
            selector = this.parseArrayToString(selectorList);
        }
        else if (element.getRootNode() instanceof DocumentFragment) {
            let tempElement = element;
            do {
                selectorList.unshift(this.getUniqueCssSelector(tempElement, selectorConf, tempElement.getRootNode(), selectorFormat));
                selectorList.unshift("|shadowDOM|");
                tempElement = tempElement.getRootNode().host;
            } while (tempElement.getRootNode() instanceof DocumentFragment);
            selectorList.unshift(this.getUniqueCssSelector(tempElement, selectorConf, document, selectorFormat));
            selector = this.parseArrayToString(selectorList);
        }
        return selector;
    }

    getElement(selector, elementMeta = null) {
        try {
            let selectorList = this.parseStringToArray(selector),
                element = null,
                tempSelector, contextTag;
            this.context = document;
            do {
                tempSelector = selectorList.shift().trim();
                element = (tempSelector != '') ? this.context.querySelector(tempSelector) : element;
                if (!element || selectorList.length == 0) {
                    break;
                }
                contextTag = selectorList.shift().trim().toLowerCase();
                if (contextTag == 'iframe') {
                    this.context = element.contentDocument;
                } else if (contextTag == 'shadowdom') {
                    this.context = element.shadowRoot;
                } else {
                    break;
                }
            } while (selectorList.length > 0);
            
            // If no filters are enabled, return the default element
            let hasTextFilter = elementMeta && elementMeta.text && elementMeta.text.filterEnabled;
            let hasMatchOrderFilter = elementMeta && elementMeta.matchOrder && elementMeta.matchOrder.filterEnabled;
            
            if (!hasTextFilter && !hasMatchOrderFilter) {
                this.context = document;
                return element;
            }
            
            // Get all matching elements for filtering
            let elements = tempSelector ? Array.from(this.context.querySelectorAll(tempSelector)) : [element];
            
            // Apply text filter if enabled
            if (hasTextFilter && elements.length > 0) {
                const { content, options } = elementMeta.text;
                elements = this.findElementsByText(elements, content, options);
            }
            
            // Apply matchOrder filter if enabled
            if (hasMatchOrderFilter && elements.length >= elementMeta.matchOrder.selectedIndex) {
                element = elements[elementMeta.matchOrder.selectedIndex - 1];
            } else if (elements.length > 0) {
                element = elements[0];
            }

            this.context = document;
    
            return element || null;
        }
        catch (error) {
            return null;
        }
    }
    

    getAllElement(selector, elementMeta = null, context = document) {
        try {
            let selectorList = this.parseStringToArray(selector);
            let elements;
            
            if (selectorList.length > 1 && (selectorList.includes("|iframe.cross|") || selectorList.length % 2 == 0)) {                
                let element = this.getElement(selector, elementMeta);
                elements = (element) ? [element] : [];
            } else if (selectorList.length > 1) {
                let contextElementSelector = selectorList.slice(0, selectorList.length - 2).join('|');
                let contextTag = selectorList[selectorList.length - 2].trim().toLowerCase();
                let tempSelector = selectorList[selectorList.length - 1].trim();
                
                let contextElement = this.getElement(contextElementSelector);
                if (contextElement) {
                    let queryContext = null;
                    if (contextTag === 'iframe' && contextElement.contentDocument) {
                        queryContext = contextElement.contentDocument;
                    } else if (contextTag === 'shadowdom' && contextElement.shadowRoot) {
                        queryContext = contextElement.shadowRoot;
                    }
                    
                    if (queryContext && tempSelector) {
                        elements = Array.from(queryContext.querySelectorAll(tempSelector));
                    } else {
                        elements = [];
                    }
                } else {
                    elements = [];
                }
            } else {
                elements = (selector.trim() != '') ? Array.from(document.querySelectorAll(selector)) : [];
            }
    
            // Apply text filter if provided
            if (elementMeta && elementMeta.text && elementMeta.text.filterEnabled && elements.length > 0) {
                const { content, options } = elementMeta.text;
                elements = this.findElementsByText(elements, content, options);
            }
            if (elementMeta && elementMeta.matchOrder && elementMeta.matchOrder.filterEnabled && elements.length > elementMeta.matchOrder.selectedIndex) {
                return elements[elementMeta.matchOrder.selectedIndex - 1];
            }
    
            return elements;
        } catch (error) {
            return [];
        }
    }
    

    findElementsByText(nodeList, text, options = {}) {
        const { caseSensitive = false, exactMatch = false } = options;
        const elements = Array.from(nodeList);
        let matches = [];
    
        for (let element of elements) {
            let elementText = element.textContent || element.innerText || '';
            elementText = elementText.replace(/[\n\r\t\f\v]+/g, ' ').replace(/\s+/g, ' ').trim();
            let isMatch = false;
            text = text.replace(/[\n\r\t\f\v]+/g, ' ').replace(/\s+/g, ' ').trim();
    
            if (exactMatch) {
                isMatch = caseSensitive
                    ? elementText.trim() === text
                    : elementText.trim().toLowerCase() === text.toLowerCase();
            } else {
                isMatch = caseSensitive 
                    ? elementText.includes(text)
                    : elementText.toLowerCase().includes(text.toLowerCase());
            }
    
            if (isMatch) {
                matches.push(element);
            }
        }
        return matches.length > 0
            ? matches
            : elements;
    }
    

    //unique css-selector Utility

    getUniqueCssSelector(element, selectorConf, context, selectorFormat) {
        this.context = (context) ? context : document;
        let path = [];
        this.checkedComby = [];
        let counter = 0;
        let elementMeta = { text: null };
        while (element) {
            let json = {
                comby: []
            }

            //tagname
            let selector = element.tagName.toLowerCase();
            json.tagName = selector;
            //id
            if (element.id && selectorConf.id) {
                let id,
                    numberHandling = selectorFormat && selectorFormat.id && selectorFormat.id.numberHandling;
                
                if (!/\d/.test(element.id)) {
                    id = "#" + element.id;
                } else {
                    switch (numberHandling) {
                        case "ignore":
                            id = this.isValidID(element.id) ? this.idToGenericSelector(element.id) : `[id='${element.id}']`;
                            break;
                        case "exclude":
                            break;
                        default:
                            id = `[id='${element.id}']`;
                            break;
                    }
                }
                id && json.comby.push(id);
            }

            //data-attribute
            if (element.dataset && Object.keys(element.dataset).length && selectorConf.dataattribute) {
                for (let data in element.dataset) {
                    if (element.dataset[data]) {
                        data = `[data-${data}="${element.dataset[data]}"]`;
                        json.comby.push(data);
                    }
                }
            }

            if (element.hasAttributes()) {
                // not considering - href && src && for && name
                const attributes = ['type', 'title'];
                for (const attr of attributes) {
                    if (element.hasAttribute(attr)) {
                        const attrValue = element.getAttribute(attr);
                        if (attrValue) {
                            json.comby.push(`[${attr}="${attrValue}"]`);
                        }
                    }
                }
            }

            //classname
            if (element.classList.length != 0 && selectorConf.classname) {
                let classes = element.classList;
                classes = Array.from(classes, (classString) => "." + classString);
                json.comby = json.comby.concat(classes);
                json.comby = json.comby.length > 2 ? this.getSelectorCombination(json.comby) : json.comby;
            }

            //nth child
            let sibling = element;
            let nth = 0;
            while (sibling) {
                sibling = sibling.previousElementSibling;
                nth++;
            }
            json.comby.push(`:nth-child(${nth})`);

            if (this.checkedComby.length > 100) {
                this.checkedComby = this.checkedComby.slice(-100);
            }
            element = element.parentElement;
            counter++;
            path.unshift(json);
            let uniqueSelector = this.getUniqueSelectorCombination(json);
            if (uniqueSelector) {
                this.context = document;
                return uniqueSelector;
            }
        }
    }

    isValidID(id) {
        // valid for direct #id usage without escaping
        return /^[A-Za-z_-][A-Za-z0-9_-]*$/.test(id);
    }

    isValidClass(className) {
        //if it contains special character , then it is not valid classname
        let pattern = RegExp(/[:;'/*&#@$%^()?]/);
        return (!pattern.test(className)) && (!className.includes('.'))
        // `#${element.id}`;
    }

    getSelectorCombination(list) {
        let set = [], listSize = list.length, combinationsCount = (1 << listSize);
        for (let i = 1; i < combinationsCount; i++) {
            let combination = [];
            for (let j = 0; j < listSize; j++) {
                if ((i & (1 << j)))
                    combination.push(list[j]);
            }
            combination.length <= 2 ? set.push(combination.join("")) : '';
        }
        return set;

    }

    getUniqueSelectorCombination(elementConf) {
        for (let i = 0; i < elementConf.comby.length; i++) {
            elementConf.comby[i] = elementConf.tagName + elementConf.comby[i];
        }
        return this.validateSelectorCombinations(elementConf.comby);
    }

    validateSelectorCombinations(comby) {
        let newCheckedComby = [];
        for (let i = 0; i < comby.length; i++) {
            try {
                this.context.querySelectorAll(comby[i]);
            }
            catch (err) {
                continue;
            }
            if (this.checkedComby.length) {
                for (let j = 0; j < this.checkedComby.length; j++) {
                    let selector = comby[i] + " > " + this.checkedComby[j];
                    let selLength = this.context.querySelectorAll(selector).length;
                    if (selLength == 1) {
                        return selector;
                    } else if (selLength > 1) {
                        newCheckedComby.push(selector);
                    }
                }
            } else if (this.context.querySelectorAll(comby[i]).length == 1) {
                return comby[i];
            } else {
                newCheckedComby.push(comby[i]);
            }
        }
         
        this.checkedComby = newCheckedComby;
        return false;
    }

    idToGenericSelector(id) {
        if (!/\d/.test(id)) {
            return "#" + id;
        }

        // extract non-numeric segments
        var parts = id.split(/[0-9]+/).filter(Boolean);

        var selectors = [];

        // prefix (non-numeric start)
        if (!/^[0-9]/.test(id) && parts[0]) {
            selectors.push("[id^='" + parts[0] + "']");
        }

        return selectors.join("");
    }

    parseStringToJSON(jsonStr) {
        try {
            let json = JSON.parse(jsonStr);
            return json;
        } catch (error) {
            return false;
        }
    }

    getElementMeta(element, selector, existingMeta = null) { 
        let elementMeta = {
            text: {
                content: ''
            }, 
            matchOrder: {
                selectedIndex: 1,
                matchCount: 1
            }
        };
        let elementContext = element.getRootNode() instanceof ShadowRoot ? element.getRootNode().host : element.ownerDocument;
        let validSelector = this.parseStringToArray(selector).filter(sel => sel.trim() != '').pop();
        let matchedElementsArr = Array.from(elementContext.querySelectorAll(validSelector));
        
        // If text filter is enabled, filter elements by text content first
        if (existingMeta && existingMeta.text && existingMeta.text.filterEnabled && existingMeta.text.content) {
            matchedElementsArr = this.findElementsByText(matchedElementsArr, existingMeta.text.content, existingMeta.text.options || {});
        }
        
        let order = matchedElementsArr.indexOf(element) + 1;
        if (matchedElementsArr.length > 1) {
            elementMeta.matchOrder.selectedIndex = order > 0 ? order : 1;
            elementMeta.matchOrder.matchCount = matchedElementsArr.length;
        }
        // Preserve text content from existingMeta if available, otherwise extract from element
        if (existingMeta && existingMeta.text && existingMeta.text.filterEnabled && existingMeta.text.content) {
            elementMeta.text = existingMeta.text;
        } else if (element.textContent) {
            let text = element.textContent || element.innerText || '';
            let escapedText = text.replace(/[\n\r\t\f\v]+/g, ' ').replace(/\s+/g, ' ').trim();
            if (text && text.length > 0 && text.length < 30) {
                elementMeta.text = {content: escapedText};
            }
        }
        return elementMeta;
    }

}
// $Id$

class IframeContentSelector {

    constructor(parentCallback) {
        this.parentCallback = parentCallback;
        this.windowContext = null;
        this.documentContext = null;
        this.elementsRef = {
            sameOriginIframes: [],
            crossOriginIframes: [],
            // iframeNodes: [],
            cursorStyleTags: [],
            contentDocuments: [],
        };
        this.crossOriginWarningShowedIframe = null;
        this.activeFrame = null;
        this.activeDimensions = {};
        this.iframeInterval = null;
        this.Util = WalkthroughBuilderSDKUtility;
        this.eventHandlers = this.getBoundMethodsRef();

    }

    getBoundMethodsRef() {
        return {
            fetchTargetFromIframe: this.fetchTargetFromIframe.bind(this),
            setTargetFromIframe: this.setTargetFromIframe.bind(this),
            escapeKeyHandler: this.escapeKeyHandler.bind(this),
        }
    }

    startIframeSelector() {
        this.elementsRef.contentDocuments = [];
        this.elementsRef.sameOriginIframes = [];
        this.elementsRef.crossOriginIframes = [];
        this.elementsRef.cursorStyleTags = [];
        var self = this;
        self.iterateIfranes(document);
        this.iframeInterval = setInterval(() => self.iterateIfranes(document), 1000);
    }

    iterateIfranes(documentContext = document) {
        const iframes = documentContext.querySelectorAll("iframe");
        iframes.forEach(iframe => {
            if (iframe.contentDocument) {
                this.handleSameOriginIframe(iframe);
                this.iterateIfranes(iframe.contentDocument);
            }
        });
      
    }

    handleSameOriginIframe(element) {
        (!this.elementsRef.sameOriginIframes.includes(element))
            ? this.elementsRef.sameOriginIframes.push(element) : '';
        if (!this.elementsRef.contentDocuments.includes(element.contentDocument)) {
            this.elementsRef.contentDocuments.push(element.contentDocument);
            this.setIframeEventListeners(element.contentDocument);
            this.elementsRef.cursorStyleTags.push(this.changeCursorStyle(element.contentDocument));
        }
    }

    handleCrossOriginIframe(element) {
        if (!this.elementsRef.crossOriginIframes.includes(element)) {
            this.elementsRef.crossOriginIframes.push(element);
            this.setCrossOriginIframeHandlers(element);
        }
    }

    clearIframeHandlers() {
        if (this.iframeInterval) {
            clearInterval(this.iframeInterval);
            this.iframeInterval = null;
        }
        this.elementsRef.sameOriginIframes.forEach((element, i) => {
            if (element && element.contentDocument) {
                this.removeIframeEventListeners(element.contentDocument);
                this.elementsRef.cursorStyleTags[i].remove();
            }
        });
        this.elementsRef.sameOriginIframes = [];
        this.elementsRef.crossOriginIframes = [];
        this.elementsRef.contentDocuments = [];
        this.elementsRef.cursorStyleTags = [];
    }

    setIframeEventListeners(contentDocument) {
        contentDocument.addEventListener("mousemove", this.eventHandlers.fetchTargetFromIframe, true);
        contentDocument.addEventListener('keydown', this.eventHandlers.escapeKeyHandler, true);
        contentDocument.addEventListener("click", this.eventHandlers.setTargetFromIframe, true);
        contentDocument.addEventListener('mousedown', this.preventEventBehaviours, true);
        contentDocument.addEventListener('mouseup', this.preventEventBehaviours, true);
    }

    changeCursorStyle(contentDocument) {
        let styleConf = {
            tagName: "style",
            id: "walkthroughCursorStyle",
            htmlContent: '* { cursor: crosshair !important; }'
        }
        let cursorStyleTag = this.Util.createHtmlElement(styleConf);
        contentDocument.documentElement  ? contentDocument.documentElement.appendChild(cursorStyleTag) : "";
        return cursorStyleTag;
    }

    fetchTargetFromIframe(event) {
        this.preventEventBehaviours(event);
        this.activeFrame = event.view.frameElement;
        let params = {
            action: "fetchedTarget",
            event: event
        };
        this.parentCallback(params);
    }

    preventEventBehaviours(event) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
    }

    setTargetFromIframe(event) {
        let params = { action: "updateTarget", event: event };
        this.parentCallback(params);
    }
    escapeKeyHandler(event) {
        let params = { action: "escape", event: event };
        this.parentCallback(params);
    }

    removeIframeEventListeners(contentDocument) {
        contentDocument.removeEventListener("mousemove", this.eventHandlers.fetchTargetFromIframe, true);
        contentDocument.removeEventListener('keydown', this.eventHandlers.escapeKeyHandler, true);
        contentDocument.removeEventListener("click", this.eventHandlers.setTargetFromIframe, true);
        contentDocument.removeEventListener('mousedown', this.preventEventBehaviours, true);
        contentDocument.removeEventListener('mouseup', this.preventEventBehaviours, true);
    }
}// $Id$

class Navigation {

    constructor(onEndNavigation) {
        this.onEndNavigationCallback = onEndNavigation;
        this.elementsRef = {
            endNavigationBtn: null,
            endNavigationBtnStyle: null
        };
        this.eventHandlers = this.getBoundMethodsRef();
        this.Util = WalkthroughBuilderSDKUtility;
        this.closedContainer = new InproductContainer('walkthrough-navigation-info');
    }

    getBoundMethodsRef() {
        return {
            endNavigationMode: this.endNavigationMode.bind(this)
        };
    }

    startNavigation() {
        this.closedContainer.initialize();
        this.createEndNavigationBtn();
        this.setNavigationEventListeners();
    }

    createEndNavigationBtn() {
        let btnConf = {
            tagName: "div",
            id: "walkthroughEndNavigationBtn",
            htmlContent: this.getEndNavigationBtnHtml()
        }
        this.elementsRef.endNavigationBtn = this.Util.createHtmlElement(btnConf);
        this.closedContainer.getShadowRoot().appendChild(this.elementsRef.endNavigationBtn);
        let btnStyleConf = {
            tagName: "style",
            id: "walkthrougEndNavigationBtnStyle",
            htmlContent: this.getEndNavigationBtnStyle()
        };
        this.elementsRef.endNavigationBtnStyle = this.Util.createHtmlElement(btnStyleConf);
        this.closedContainer.getShadowRoot().appendChild(this.elementsRef.endNavigationBtnStyle);
    }

    getEndNavigationBtnHtml() {
        return `<div id="borderanimation"></div>
                <div id="text">Click here to resume creating your walk-through flow.</div>`;
    }

    getEndNavigationBtnStyle() {
        return `#walkthroughEndNavigationBtn {
                  height: max-content;
                  width: max-content;
                  text-align: center;
                  cursor: pointer;
                  z-index: 9999999999999;
                  padding: 2px;
                  position: fixed;
                  inset: auto 0 5vw;
                  margin-left: auto;
                  margin-right: auto;
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  background: #00232e;
                  border-radius: 5px;
                  box-shadow: #0000009e -1px 7px 12px;
                  overflow: hidden;
                  transition: 0.2s ease-in-out;
                }

                #walkthroughEndNavigationBtn.hide {
                  inset: auto 0px -5vw;
                }

                #walkthroughEndNavigationBtn>#text {
                  width: max-content;
                  max-width: 30vw;
                  min-width: 8vw;
                  height: 2.9vw;
                  background-color: #00232e;
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  border-radius: 0.2vw;
                  padding: 0 1.75vw;
                  font-size: 0.9vw;
                  letter-spacing: 0.035em;
                  color: #ffffffef;
                }

                #walkthroughEndNavigationBtn>#borderanimation {
                  animation: rotate 2s linear infinite;
                  background: linear-gradient(90deg, rgba(0, 0, 0, 0) 23%, rgb(0 238 222) 100%);
                  width: 40vw;
                  height: 40vw;
                  position: absolute;
                  z-index: -1;
                }

                @keyframes rotate {
                  0% {
                    transform: rotate(1turn);
                  }
                }`
    }

    setNavigationEventListeners() {
        this.elementsRef.endNavigationBtn.addEventListener("click", this.eventHandlers.endNavigationMode);
    }

    endNavigationMode() {
        this.elementsRef.endNavigationBtn.removeEventListener("click", this.eventHandlers.endNavigationMode);
        this.elementsRef.endNavigationBtn.remove();
        this.elementsRef.endNavigationBtnStyle.remove();
        this.closedContainer.destroy();
        this.onEndNavigationCallback();
    }

}// $Id$
class WalkthroughBuilderSDKUtility {

    static cqs = new CustomQuerySelector();

    static createHtmlElement(elementConf) {
        let element = document.createElement((elementConf.tagName ? elementConf.tagName : "div"));
        elementConf.id ? element.setAttribute("id", elementConf.id) : '';
        elementConf.className ? element.setAttribute("class", elementConf.className) : '';
        element.innerHTML += (elementConf.htmlContent) ? elementConf.htmlContent : '';
        return element;
    }

    static setElementStyle(element, styleObj) {
        for (let styleType in styleObj) {
            element.style[styleType] = styleObj[styleType];
        }
    }

    static getElement(cssSelector, elementMeta = null) {
        return this.cqs.getElement(cssSelector, elementMeta);
    }

    static getElementDimensions(element) {
        return this.cqs.getElementDimensions(element);
    }

    static getSelectorMatchStatus(cssSelector) {
        let elementList = WalkthroughBuilderSDKUtility.cqs.getAllElement(cssSelector);
        return (elementList.length == 1) ?
            "foundUnique" : ((elementList.length > 1) ?
                "foundMultiple" : "notFound");
    }

    static preventEventBehaviours(event) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
    }

    static getCurrentUrl() {
        return window.location.href;
    }

    static scrollToTarget(targetElement, behavior = "smooth") {
        targetElement.scrollIntoView({ behavior: behavior, block: "center", inline: "nearest" });
    }

    static parseStringToJSON(str) {
        try {
            let json = JSON.parse(str);
            return json;
        } catch (e) {
            return false;
        }
    }

}
// $Id$

class InproductContainer {

    constructor(tag) {
        this.shadowRoot;
        this.host;
        this.observer;
        this.hostTagName = tag || 'mics-container';
        this.parentElement = document.documentElement
    }

    initialize() {
        this.createHost();
        this.attachShadowRoot();
        this.setupObserver();
        this.startHostObserver()
        this.blockHostElementRemoval();
        return this.shadowRoot;
    }

    createHost() {
        const host = document.createElement(this.hostTagName);
        host.setAttribute('data-mics-inproduct-container', '');
        host.setAttribute('mics-inproduct-container', '');
        host.setAttribute('micsInproductContainer', '');
        host.style.all = 'initial'; // reset any inherited styles
        document.documentElement.appendChild(host);
        this.host = host;
    }

    attachShadowRoot() {
        this.shadowRoot = this.host.attachShadow({ mode: 'closed' });
    }

    getShadowRoot() {
        return this.shadowRoot;
    }

    setupObserver() {
        this.observer = new MutationObserver((mutations) => {
            for (const m of mutations) {
                if (m.type === 'attributes' && m.target === this.host) {
                    this.stopHostObserver();
                    this.host.removeAttribute(m.attributeName);
                    this.host.setAttribute('data-mics-inproduct-container', '');
                    this.host.setAttribute('mics-inproduct-container', '');
                    this.host.setAttribute('micsInproductContainer', '');
                    this.startHostObserver();
                }
            }
        });
    }

    blockHostElementRemoval() {
        this.host.remove = () => {
            if (this.canRemoveHost) {
                this.host.remove = HTMLElement.prototype.remove;
                this.host.remove();
                return;
            }
            console.warn('Attempted to remove inproduct container');
        };
    }

    setContent(html) {
        const template = document.createElement('template');
        template.innerHTML = html.trim();
        this.shadowRoot.innerHTML = '';
        this.shadowRoot.appendChild(template.content.cloneNode(true));
    }

    getHost() {
        return this.host;
    }

    startHostObserver() {
        this.observer.observe(this.host, { attributes: true });
    }

    stopHostObserver() {
        this.observer.disconnect();
    }

    setStyleToHost(styleObj) {
        this.stopHostObserver()
        for (let styleType in styleObj) {
            this.host.style[styleType] = styleObj[styleType];
        }
        this.startHostObserver();
    }

    setAttributesToHost(attributes) {
        this.stopHostObserver();
        for( let name in attributes ){
            this.host.setAttribute(name, attributes[name] || '');
        }
        this.startHostObserver();
    }

    destroy() {
        this.observer.disconnect();
        this.canRemoveHost = true;
        this.host.remove();
        this.canRemoveHost = false;
    }
}// $Id$

class WalkthroughTargetElementHandler {

    constructor( selector, elementMeta = null ) {
        this.selector = selector;
        this.isValid = false;
        this.isHidden = true;
        this.dimensions = this.getDefaultDimensions();
        this.isCrossOrigin;
        this.validationInterval = 500;
        this.matchStatus = '';
        this.onClick; // method
        this.click; // method
        this.clear; // method
        this.remove_onClick; // method
        this.fetchElementData; // method
        this.callbackMethods = { // methods
            domObserver: '',
            onClick: '',
            click: '',
            clear: '',
            remove_onClick: '',
        };
        this.eventOptions = {
            onClick: {},
        };
        this.element = '';
        this.cqs = new CustomQuerySelector();
        this.domObserver;
        this.elementFetchIntervalId;
        this.hiddenElementCheckIntervalId;
        this.crossOriginElementData = {
            iframeElement: {
                status: "notFound",
                isValid: false,
                selector: '',
                observer: '',
                isHidden: true,
                updatedDimensions: this.getDefaultDimensions(),
            },
            childElement: {
                status: "notFound",
                isValid: false,
                selector: '',
                isHidden: true,
                updatedDimensions: this.getDefaultDimensions(),
            },
        };
        this.iframeRegistry = InProduct_CrossOriginMessenger.instance;
        this.Util = WalkthroughUtility;
        this.scrollCounter = { count: 0, limit: 4 };
        this.iframeScrollCounter = { count: 0, limit: 2 };
        this.elementMeta = elementMeta;
        this.init();
    } 
    
    checkCrossOrigin() {
        if (this.selector.includes('|iframe.cross|')) {
            const parts = this.selector.split('|iframe.cross|');
            this.crossOriginElementData.iframeElement.selector = parts[0];
            this.crossOriginElementData.childElement.selector = parts.slice(1).join('|iframe.cross|');
            return true;
        }
        return false;
    }

    init() {
        this.isCrossOrigin = this.checkCrossOrigin();
        this.Util.logger( "Walkthrough: Target Element 'Initiated'; Id = " + this.selector, "group" );
        if (this.isCrossOrigin) {
            this.onClick = this.onCrossOriginElementClick;
            this.click = this.clickOnCrossOriginElement;
            this.clear = this.clearCrossOriginObservers;
            this.remove_onClick = this.removeCrossOriginClickListener;
            this.fetchElementData = this.handleIframeElement_DomChange;
            this.iframeRegistry.targetElementCallback = this.processIframeMsg.bind(this);
            this.fetchCrossOriginIframe_onInterval();
        } else {
            this.onClick = this.onElementClick;
            this.click = this.clickElement;
            this.clear = this.clearElementObservers;
            this.remove_onClick = this.remove_clickListener;
            this.fetchElementData = this.handleDomChange;
            this.fetchElementOnInterval();
        }
    }

    onElementClick(callback, options) {
        this.callbackMethods.onClick = callback;
        const root = this.element.ownerDocument || this.element;
        const userOptions = options || {};
        (userOptions.capture) ? '' : userOptions.capture = true;
        const handler = (event) => {
            if (!event || !event.composedPath || !event.composedPath().includes(this.element)) {
                return;
            }
            this.Util.logger("Walkthrough: Target Element 'Clicked By User'; Id = " + this.selector, "group");
            callback ? callback() : '';
            this.handleDomChange(this.dimensions);
            if (this.eventOptions.onClick.userOptions && this.eventOptions.onClick.userOptions.once) {
                this.remove_clickListener();
            }
        };
        this.eventOptions.onClick = {
            handler: handler,
            root: root,
            userOptions: userOptions
        };
        root.addEventListener('click', handler, userOptions);
        this.Util.logger("Walkthrough: Target Element 'ClickListener Set'; Id = " + this.selector, "group");
    }

    clickElement(callback) {
        this.element.dispatchEvent(this.createMouseEvent('click'));
        this.element.dispatchEvent(this.createMouseEvent('mousedown'));
        this.element.dispatchEvent(this.createMouseEvent('mouseup'));
        this.Util.logger( "Walkthrough: Target Element 'Triggered'; Id = "+this.selector, "group" );
        callback? callback() : '';
    }

    clearElementObservers() {
        this.domObserver? this.domObserver.destroyDOMObservers() : '';
        this.callbackMethods.onClick ? this.remove_clickListener() : '';
        window.clearInterval(this.elementFetchIntervalId);
        window.clearInterval(this.hiddenElementCheckIntervalId);
        this.Util.logger( "Walkthrough: Target Element 'Cleared'; Id = "+this.selector, "groupEnd" );
    }

    remove_clickListener(callback) {
        const onClickState = this.eventOptions.onClick;
        if (onClickState && onClickState.handler && onClickState.root) {
            onClickState.root.removeEventListener('click', onClickState.handler, onClickState.userOptions);
        }
        this.callbackMethods.onClick = '';
        this.eventOptions.onClick = {};
        callback ? callback() : '';
    }

    observeElement( domChangeHandler ) {
        this.domObserver = new DOMObserver(domChangeHandler);
        this.domObserver.setTargetElement(this.element);
        this.Util.logger( "Walkthrough: 'Observing' Target Element; Id = "+this.selector, "group" );
    }

    handleDomChange(updatedDimensions) {
        let element = this.cqs.getElement(this.selector, this.elementMeta);

        if (element == this.element) {
            this.dimensions = updatedDimensions || this.cqs.getElementDimensions(this.element);
            this.isValid = true;
            this.isHidden = this.Util.isElementHidden(this.element, this.scrollCounter, this.iframeScrollCounter);
        } else if (element) { 
            this.domObserver.destroyDOMObservers();
            this.fetchElementOnInterval();
        } else {
            this.isValid = false;
            this.isHidden = true;
            this.dimensions = this.getDefaultDimensions();
            this.clearElementObservers();
            this.fetchElementOnInterval();
        }
        this.Util.logger("Walkthrough: DOM Changes Observed; Id = " + this.selector, "group");
        this.Util.logger("Walkthrough: Target Element 'Validated= " + this.isValid + "'", "group");
        this.Util.logger("Walkthrough: Target Element 'Visibility= " + !this.isHidden + "'", "groupEnd");
        this.callbackMethods.domObserver ? this.callbackMethods.domObserver() : '';
    }

    fetchElementOnInterval() {
        this.elementFetchIntervalId = window.setInterval(() => this.fetchElementFromDom(), this.validationInterval);
        this.fetchElementFromDom();
    }

    fetchElementFromDom() {
        window.clearInterval(this.hiddenElementCheckIntervalId);
        this.element = this.cqs.getElement(this.selector, this.elementMeta);
        if (this.element) {
            this.scrollCounter = { count: 0, limit: 4 };
            this.iframeScrollCounter = { count: 0, limit: 2 };
            this.observeElement(this.handleDomChange.bind(this));
            this.isValid = true;
            this.checkElementVisibilityOnInterval();
            this.dimensions = this.cqs.getElementDimensions(this.element);
            this.Util.logger( "Walkthrough: Target Element 'Fetched'; Id = "+this.selector, "group" );
            window.clearInterval(this.elementFetchIntervalId);
        } else {
            this.isValid = false;
            this.isHidden = true;
            this.dimensions = this.getDefaultDimensions();
        }
    }
    
    checkElementVisibilityOnInterval() {
        this.Util.logger( "Walkthrough: Target Element 'Visibility Check on Interval'; Id = "+this.selector, "group" );
        this.hiddenElementCheckIntervalId = window.setInterval(() => this.checkElementVisibility(), this.validationInterval);
        this.checkElementVisibility();
    }
    
    checkElementVisibility() {
        let element = this.cqs.getElement(this.selector, this.elementMeta);
        if (element != this.element || this.Util.isElementHidden(this.element, this.scrollCounter, this.iframeScrollCounter) != this.isHidden) {
            this.handleDomChange(this.dimensions);
        }
    }
    
    fetchCrossOriginIframe_onInterval() {
        this.elementFetchIntervalId = window.setInterval(() => this.fetchCrossOriginIframe(), this.validationInterval);
        this.fetchCrossOriginIframe();
    }
    
    fetchCrossOriginIframe() {
        window.clearInterval(this.hiddenElementCheckIntervalId);
        this.element = this.cqs.getElement(this.crossOriginElementData.iframeElement.selector);
        if (this.element && this.element.contentWindow && this.iframeRegistry.registeredIframeRef.includes(this.element)
            && this.iframeRegistry.registeredIframesSource.includes(this.element.contentWindow)) {
            this.scrollCounter = { count: 0, limit: 4 };
            this.iframeScrollCounter = { count: 0, limit: 2 };
            this.setCrossOriginTargetElement();
            this.observeElement(this.handleIframeElement_DomChange.bind(this));
            this.crossOriginElementData.iframeElement.isValid = true;
            this.crossOriginElementData.childElement.isValid = false;
            this.checkIframeVisibilityOnInterval();
            this.Util.logger("Walkthrough: Target Element 'Iframe Fetched'; Id = "+this.selector, "group");
            window.clearInterval(this.elementFetchIntervalId);
        } else {
            this.isValid = false;
            this.isHidden = true;
            this.crossOriginElementData.iframeElement.isValid = false;
            this.crossOriginElementData.childElement.isValid = false;
        }
    }

    checkIframeVisibilityOnInterval() {
        this.Util.logger( "Walkthrough: Target Element 'Iframe Visibility Check on Interval'; Id = "+this.selector, "group" );
        this.hiddenElementCheckIntervalId = window.setInterval(() => this.checkIframeVisibility(), this.validationInterval);
        this.checkIframeVisibility();
    }
    
    checkIframeVisibility() {
        let element = this.cqs.getElement(this.crossOriginElementData.iframeElement.selector);
        if (element != this.element || this.Util.isElementHidden(this.element, this.scrollCounter, this.iframeScrollCounter) != this.crossOriginElementData.iframeElement.isHidden) {
            this.handleIframeElement_DomChange(this.crossOriginElementData.iframeElement.updatedDimensions);
        }
    }

    setCrossOriginTargetElement() {
        this.element.contentWindow.postMessage({
            action: "setChildTargetElement", source:"inproductsdk", origin: "inproduct_parentsdk",
            payload: {
                fullSelector: this.selector, childSelector: this.crossOriginElementData.childElement.selector,
                elementMeta: this.elementMeta
            },
            mode: "walkthroughrendering"
        }, "*");
    }

    onCrossOriginElementClick( callback, options ) {
        let element = this.cqs.getElement(this.crossOriginElementData.iframeElement.selector);
        if (element && element == this.element && this.element.contentWindow ) { 
            this.element.contentWindow.postMessage({
                action: "listenTargetClick", source:"inproductsdk", origin: "inproduct_parentsdk",
                payload: { fullSelector: this.selector, eventOptions: options, elementMeta: this.elementMeta },
                mode: "walkthroughrendering"
            }, "*");
        }
        this.callbackMethods.onClick = callback || '';
        this.eventOptions.onClick = options;
    }

    clickOnCrossOriginElement( callback ) {
        this.element.contentWindow.postMessage({
            action: "triggerChildTarget", source:"inproductsdk", origin: "inproduct_parentsdk",
            payload: { fullSelector: this.selector, elementMeta: this.elementMeta },
            mode: "walkthroughrendering"
        }, "*");
        callback ? callback() : '';
    }

    clearCrossOriginObservers( callback ) {
        if (this.element && this.element.contentWindow ) { 
            this.element.contentWindow.postMessage({
                action: "clearChildTarget", source:"inproductsdk", origin: "inproduct_parentsdk",
                payload: { fullSelector: this.selector, childSelector: this.crossOriginElementData.childElement.selector },
                mode: "walkthroughrendering"
            }, "*");
        }
        window.clearInterval(this.hiddenElementCheckIntervalId);
        this.domObserver? this.domObserver.destroyDOMObservers() : '';
        window.clearInterval(this.elementFetchIntervalId);
        callback ? callback() : '';
    }

    removeCrossOriginClickListener( callback ) {
        this.callbackMethods.onClick = '';
    }

    handleIframeElement_DomChange(updatedDimensions) {
        let element = this.cqs.getElement(this.crossOriginElementData.iframeElement.selector);
        if (element == this.element) {
            this.crossOriginElementData.iframeElement.isHidden = this.Util.isElementHidden(this.element, this.scrollCounter, this.iframeScrollCounter);
            this.crossOriginElementData.iframeElement.updatedDimensions = updatedDimensions || this.cqs.getElementDimensions(this.element);
            this.element.contentWindow.postMessage({
                action: "onParentDomChange", source:"inproductsdk", origin: "inproduct_parentsdk",
                payload: {
                    fullSelector: this.selector, childSelector: this.crossOriginElementData.childElement.selector,
                    elementMeta: this.elementMeta
                 },
                mode: "walkthroughrendering"
            }, "*");
        } else if (element) {
            this.clearCrossOriginObservers();
            this.fetchCrossOriginIframe_onInterval();
        } else {
            this.isValid = false;
            this.isHidden = true;
            this.crossOriginElementData.iframeElement.isValid = false;
            this.crossOriginElementData.childElement.isValid = false;
            this.crossOriginElementData.iframeElement.isHidden = true;
            this.crossOriginElementData.childElement.isHidden = true;
            this.crossOriginElementData.iframeElement.updatedDimensions = this.getDefaultDimensions();
            this.crossOriginElementData.childElement.updatedDimensions = this.getDefaultDimensions();
            this.dimensions = this.getDefaultDimensions();
            this.clearCrossOriginObservers();
            this.fetchCrossOriginIframe_onInterval();
            this.callbackMethods.domObserver ? this.callbackMethods.domObserver() : '';
        }
        this.Util.logger("Walkthrough: DOM Changes Observed; Id = " + this.selector, "group");
        this.Util.logger("Walkthrough: Target Element 'Iframe Validated= " + this.crossOriginElementData.iframeElement.isValid + "'", "group");
        this.Util.logger("Walkthrough: Target Element 'Iframe Visibility= " + !this.crossOriginElementData.iframeElement.isHidden + "'", "groupEnd");
    }
    
    updateChildElementData(updatedData) {
        // let isElementInView;
        if (updatedData.isValid) {
            let frameDimensions = this.crossOriginElementData.iframeElement.dimensions || this.cqs.getElementDimensions(this.element);
            this.crossOriginElementData.childElement.updatedDimensions = updatedData.dimensions;
            this.dimensions = this.Util.offsetByFrameDimensions(updatedData.dimensions,[frameDimensions]);
            // isElementInView = this.checkElementNotInView();
        } else {
            this.dimensions = this.getDefaultDimensions();
        }
        this.crossOriginElementData.childElement.isValid = updatedData.isValid;
        this.isValid = updatedData.isValid;
        this.crossOriginElementData.childElement.isHidden = updatedData.isHidden;
        this.crossOriginElementData.iframeElement.isHidden = this.Util.isElementHidden(this.element, this.scrollCounter, this.iframeScrollCounter);
        this.isHidden = this.crossOriginElementData.childElement.isHidden || this.crossOriginElementData.iframeElement.isHidden;
        this.callbackMethods.domObserver ? this.callbackMethods.domObserver() : '';
        this.Util.logger("Walkthrough: Child DOM Changes Updated ; Id = " + this.selector, "group");
        this.Util.logger("Walkthrough: Target Element 'Iframe Validated= " + this.crossOriginElementData.iframeElement.isValid + "'", "group");
        this.Util.logger("Walkthrough: Target Element 'Iframe Visibility= " + !this.crossOriginElementData.iframeElement.isHidden + "'", "group");
        this.Util.logger("Walkthrough: Target Element 'Child Validated= " + this.crossOriginElementData.childElement.isValid + "'", "group");
        this.Util.logger("Walkthrough: Target Element 'Child Visibility= " + !this.crossOriginElementData.childElement.isHidden + "'", "group");
        this.Util.logger("Walkthrough: Target Element 'Iframe Updated Dimensions= " + JSON.stringify(this.crossOriginElementData.iframeElement.updatedDimensions) + "'", "group");
        this.Util.logger("Walkthrough: Target Element 'Child Updated Dimensions= " + JSON.stringify(this.crossOriginElementData.childElement.updatedDimensions) + "'", "group");
        this.Util.logger("Walkthrough: Target Element 'Validated= " + this.crossOriginElementData.childElement.isValid + "'", "group");
        this.Util.logger("Walkthrough: Target Element 'Visibility= " + !this.crossOriginElementData.childElement.isHidden + "'", "groupEnd");
    }
    
    handleChildElementClick(elementData) {
        if (elementData.fullSelector == this.selector) {
            this.callbackMethods.onClick ? this.callbackMethods.onClick() : '';
            this.removeCrossOriginClickListener();
        }
        this.Util.logger("Walkthrough: Target Element User Click In Child ; Id = " + this.selector, "group");
    }
    
    // checkElementNotInView() {
    //     try {
    //         const view = this.element.ownerDocument.defaultView;
    //         if (rect.left + rect.width <= 0 || rect.top + rect.height <= 0 ||
    //             rect.top >= view.innerHeight || rect.left >= view.innerWidth
    //         ) {
    //             return false;
    //         }

    //         const x = Math.max(0, Math.min(rect.left + rect.width / 2, view.innerWidth - 1));
    //         const y = Math.max(0, Math.min(rect.top + rect.height / 2, view.innerHeight - 1));

    //         const topElement = new CustomQuerySelector().getElementFromPoint({ x: x, y: y }, element.ownerDocument);

    //         if (!topElement || WalkthroughUtility.isWalkthroughElement(topElement)) {
    //             return false;
    //         }

    //         if (topElement === element || element.contains(topElement) || topElement.contains(element)) {
    //             return false;
    //         }

    //         return true;
    //     } catch (error) {
    //         WalkthroughUtility.logger( "Walkthrough Error: Element hidden check failed\n" + error , "error");
    //         return false;
    //     }
    // }

    getElementData() {
        return {
            dimensions: this.dimensions,
            isValid: this.isValid,
            isHidden: this.isHidden,
        }
    }

    getBoundindClientRect() {
        return this.dimensions;
    }

    validate() {
        return this.isValid;
    }

    isVisible() {
        return !this.isHidden;
    }

    createMouseEvent(eventname) {
        return new MouseEvent(eventname, {
            bubbles: true,
            cancelable: true,
            view: window
        });
    }

    getDefaultDimensions() {
        return {
            x: 0,
            y: 0,
            top: 0,
            left: 0,
            height: 0,
            width: 0,
        };
    }

    onDOMChange( callback ) {
        this.callbackMethods.domObserver = callback;
    }

    processIframeMsg(data) {
        if (data.payload.fullSelector.trim() == this.selector.trim() )
        switch (data.action) {
            case "updateTargetData":
                this.updateChildElementData(data.payload);
                break;
            case "elementTriggered":
                this.handleChildElementClick(data.payload);
                break;
            default:
                break;
        }
    }

}//$Id$
class WalkthroughBuilderSDK {

    static instance = null;

    constructor() {
        this.walkthroughConfig;  // service id, org id,
        this.builderIframeRef = null;
        this.frameOrigin = "*"; // will be replaced with tipengine domain
        this.targetElementData = {
            childElement: {
                status: "notFound",
                selector: null
            }
        };
        this.urlCheck = {
            lastUpdatedUrl: '',
            intervalId: ''
        };
        this.targetElementCheck = {
            intervalId: '',
        };
        this.eventHandlers = this.getBoundMethodsRef()
        this.messenger = new BuilderSDKMessenger(this);
        this.setMessengerConfig();
        this.cssSelector = new CssSelector(this.updateSelectedTargetElement.bind(this));
        this.builderPreview = new BuilderPreview(this.onEndPreview.bind(this));
        this.domObserver = new DOMObserver(this.updateDomChanges.bind(this));
        this.navigation = new Navigation(this.startBuilderMode.bind(this));
        this.interaction = new Interaction(this.endInteractiveMode.bind(this));
        this.customQuerySelector = new CustomQuerySelector();
        this.Util = WalkthroughBuilderSDKUtility;
        this.bundleUtil = new BundleWalkthroughUtility();
        this.editableFlowData;
        this.parentContainer = new InproductContainer('walkthrough-builder');
    }

    static getInstance() {
        if (WalkthroughBuilderSDK.instance == null) {
            WalkthroughBuilderSDK.instance = new WalkthroughBuilderSDK();
            return WalkthroughBuilderSDK.instance;
        }
        return WalkthroughBuilderSDK.instance;
    }

    getBoundMethodsRef() {
        // organised 'this' bound eventHandlers to maintain method reference
        return {
            initBuilderIframe: this.initBuilderIframe.bind(this),
            startBuilderMode: this.startBuilderMode.bind(this),
        };
    }

    initialize() {
        this.checkOngoingWalkthroughMode();
        WalkthroughBuilderSDK.instance = this;
        const iframes = document.querySelectorAll("iframe");
        iframes.forEach((iframe) => {
            if (!iframe.contentDocument) {
                iframe.contentWindow.postMessage(
                    {
                        source: "inproductsdk",
                        action: "registerIframe",
                        origin: "inproduct_parentsdk",
                        data: {},
                        mode: "walkthroughbuilder",
                    },
                    "*"
                );
            }
        });
    }

    checkOngoingWalkthroughMode() {
        let mode = window.sessionStorage.getItem("builder.ongoingWalkthroughMode");
        this.currentMode = mode;
        let walkthroughConfig = this.Util.parseStringToJSON(window.sessionStorage["micsWalkthroughConfig"])
        if (mode) {
            this.walkthroughConfig = JSON.parse(window.sessionStorage["micsWalkthroughConfig"]);

            switch (mode) {
                case "preview":
                    this.builderPreview.handleOngoingPreview(this.walkthroughConfig);
                    break;
                case "navigation":
                    this.injectBuilderIfrane();
                    this.startNavigationMode();
                    break;
                case "builder":
                    this.injectBuilderIfrane();
                    this.builderIframeRef.addEventListener("load", this.eventHandlers.startBuilderMode);
                    break;
            }
        } else if (walkthroughConfig) {
            this.startWalkthroughAction(walkthroughConfig);
        }
    }

    processMessage(msgData) {
        let mode = window.sessionStorage.getItem("builder.ongoingWalkthroughMode");
        if (!mode) {
            this.startWalkthroughAction(msgData.builderSDKData);
        }
    }

    startWalkthroughAction(walkthroughConfig) {
        switch (walkthroughConfig.action) {
            case "create":
                this.createBuilder(walkthroughConfig);
                break;
            case "edit":
                this.startEditingFlow(walkthroughConfig);
                break;
        };
    }

    injectBuilderIfrane() {
        (this.builderIframeRef == null) ? this.createBuilderIframe() : '';
        this.messenger.initializeIframeCommunication(this.builderIframeRef.contentWindow, this.frameOrigin);
    }

    createBuilder(micsWalkthroughConfig) {
        window.sessionStorage["micsWalkthroughConfig"] = JSON.stringify(micsWalkthroughConfig);
        this.walkthroughConfig = micsWalkthroughConfig;
        this.createBuilderIframe();
        this.messenger.initializeIframeCommunication(this.builderIframeRef.contentWindow, this.frameOrigin);
        this.builderIframeRef.addEventListener("load", this.eventHandlers.initBuilderIframe);
    }

    createBuilderIframe() {
        this.parentContainer.initialize();
        this.builderIframeRef = document.createElement('iframe');
        this.builderIframeRef.src = this.getFrameURL();
        this.bundleUtil.initialize(this.walkthroughConfig.workspaceConf || {});
        this.frameOrigin = (this.walkthroughConfig.iscustomdomain == true) ? location.origin : this.walkthroughConfig.micstipDomain;
        let style = {
            width: '100vw',
            position: 'fixed',
            inset: '0',
            border: 'none',
            zIndex: '1000000000000000000000000000000000000',
            backgroundColor: "white"
        };
        this.Util.setElementStyle(this.builderIframeRef, style);
        this.parentContainer.getShadowRoot().appendChild(this.builderIframeRef);
        this.hideBuilder();
    }

    getFrameURL() {
        let frameUrl,scope = this.walkthroughConfig.isDap ? "&Scope=Enterprise" : "";
        if (Inproductutility.validateTipDomain(this.walkthroughConfig.micstipDomain)) {
            frameUrl = this.walkthroughConfig.micstipDomain + "/jsp/walkthroughBuilder.jsp?frameorigin=" + location.origin +scope;
            this.walkthroughConfig.iscustomdomain = false;
        }
        else {
            frameUrl = location.origin + "/mics/jsp/walkthroughBuilder.jsp?frameorigin=" + location.origin+scope;
            this.walkthroughConfig.iscustomdomain = true;
        }
        window.sessionStorage["micsWalkthroughConfig"] = JSON.stringify(this.walkthroughConfig);
        return frameUrl;
    }

    initBuilderIframe() {
        this.sendCurrentUrlToIframe();
        (this.editableFlowData) ?
            this.messenger.messageToBuilderIframe(
                "initEditFlow",
                { "micsWalkthroughConfig": this.walkthroughConfig, "flowData": this.editableFlowData, "flowStartingUrl": this.Util.getCurrentUrl() }
            ) :
            this.messenger.messageToBuilderIframe(
                "initBuilder",
                { "micsWalkthroughConfig": this.walkthroughConfig }
            );
        this.startBuilderMode();
    }

    startBuilderMode() {
        this.checkUrlOnInterval();
        this.showBuilder();
        window.sessionStorage.setItem("builder.ongoingWalkthroughMode", "builder");
    }

    onIframeLoaded() {
        this.builderIframeRef.style.backgroundColor = "unset";
    }
    setChildElement(selector) {
        var { isCrossOrigin, validSelector, invalidSelector } = this.checkSelectorIsInCrossOrigin(selector);
        this.targetElementData.selector = validSelector;
        if (isCrossOrigin) {
            this.targetElementData.childElement.selector = invalidSelector;
            this.targetElementData.childElement.status = "notFound";
        }
        else {
            this.targetElementData.childElement.selector = null;
            this.targetElementData.childElement.status = "foundUnique";
        }
    }
    showBuilder() {
        this.currentMode = "builder";
        let previousMode = window.sessionStorage.getItem("builder.ongoingWalkthroughMode");
        if (previousMode && previousMode != "builder") {
            window.setTimeout(() => {
                this.builderIframeRef.style.height = "100vh";
                this.builderIframeRef.contentWindow.focus();
            }, 500);
        } else {
            this.builderIframeRef.style.height = "100vh";
            this.builderIframeRef.contentWindow.focus();
        }
    }

    hideBuilder() {
        this.builderIframeRef.style.height = "0px";
        window.focus();
    }

    checkUrlOnInterval() {
        this.sendCurrentUrlToIframe();
        this.urlCheck.lastUpdatedUrl = this.Util.getCurrentUrl();
        window.clearInterval(this.urlCheck.intervalId);
        this.urlCheck.intervalId = window.setInterval(
            () => {
                if (this.urlCheck.lastUpdatedUrl != this.Util.getCurrentUrl()) {
                    this.sendCurrentUrlToIframe();
                    this.urlCheck.lastUpdatedUrl = this.Util.getCurrentUrl();
                }
            },
            500
        );
    }

    startCssSelectorMode(selectorConf, selectorFormat) {
        this.currentMode = "selector";
        this.hideBuilder();
        (selectorConf) ? this.cssSelector.setSelectorConf(selectorConf) : null;
        this.cssSelector.setSelectorFormat(selectorFormat);
        this.cssSelector.startSelectorMode();
    }

    validateCssSelector(selector) {
        this.messenger.messageToBuilderIframe(
            "cssSelectorValidated",
            { "cssSelectorMatch": this.Util.getSelectorMatchStatus(selector) }
        );
    }

    sendCurrentUrlToIframe() {
        this.messenger.messageToBuilderIframe(
            "currentUrl",
            { "pageUrl": this.Util.getCurrentUrl() }
        );
    }

    startNavigationMode() {
        window.sessionStorage.setItem("builder.ongoingWalkthroughMode", "navigation");
        this.hideBuilder();
        this.navigation.startNavigation();
    }

    startBuilderPreview(flowStartingUrl, flowData) {
        window.sessionStorage.setItem("builder.ongoingWalkthroughMode", "preview");
        this.hideBuilder();
        this.builderPreview.startPreview(flowStartingUrl, flowData);
    }
    updateSelectedTargetElement(selectedElementData) {
        window.top == window ? this.stopDomObserversForPreviousStep() : "";
        let response = {}, element;
        response.selectedElementData = selectedElementData;
        this.currentMode = null;
        if (selectedElementData.selector != '') {
            response.status = "selected";
            element = this.Util.getElement(selectedElementData.selector);
            response.selectedElementMeta = this.customQuerySelector.getElementMeta(element, selectedElementData.selector);
            this.Util.scrollToTarget(element, "instant");
            var selectedElementResponse = this.getSelectedElementResponse(selectedElementData);
            this.targetElementData.selector = selectedElementData.selector;
            this.targetElementData.dimensions = this.Util.getElementDimensions(element);
            this.targetElementData.childElement.status = "notFound";
            this.targetElementData.childElement.selector = null;
            this.targetElementData.elementMeta = response.selectedElementMeta;
            this.domObserver.setTargetElement(element);
            response.selectedElementData.productMeta = selectedElementResponse.productMeta;
            response.selectedElementData.cssselectorMeta = selectedElementResponse.cssselectorMeta;
            response.selectedElementData.dimensions = this.parseDimensions(selectedElementData.dimensions);
        } else {
            response.status = "exited";
        }
        this.sendResponse("cssSelectorModeResponse", { response: response });
    }
    getSelectedElementResponse(selectedElementData) {
        if (window.top != window) {
            return { productMeta: {}, cssselectorMeta: {} };
        }
        var selectedElementResponse = this.findProductBySelector(selectedElementData.selector);
        return { productMeta: selectedElementResponse.productMeta, cssselectorMeta: selectedElementResponse.cssselectorMeta };
    }
    parseDimensions(dimensions) {
        var isBoundingClientRectResponse = dimensions && typeof dimensions.toJSON === "function";
        if (isBoundingClientRectResponse) {
            return { x: dimensions.x, y: dimensions.y, top: dimensions.top, left: dimensions.left, height: dimensions.height, width: dimensions.width, bottom: dimensions.bottom, right: dimensions.right };
        }
        return dimensions;
    }
    sendResponse(action, data) {
        this.messenger.messageToBuilderIframe(
            action,
            data
        );
        window.top == window ? this.showBuilder() : "";
    }
    findProductBySelector(cssSelector) {
        var productMeta = { url_product_name: this.walkthroughConfig.servicename, cssselector_product_name: this.walkthroughConfig.servicename };
        var cssselectorMeta = { bundle_cssselector: "", product_cssselector: cssSelector };
        if (this.walkthroughConfig.isDap) {
            var product_type = this.walkthroughConfig.workspaceConf.product_type;
            var currentProductName = this.walkthroughConfig.workspaceConf.activeWorkspace.product_name;
            productMeta = { url_product_name: currentProductName, cssselector_product_name: currentProductName };
            cssselectorMeta = { bundle_cssselector: "", product_cssselector: cssSelector };
            switch (product_type) {
                case "bundle":
                    var bundleMetas = this.bundleUtil.getBundleMetas(cssSelector);
                    productMeta = bundleMetas.productMeta;
                    cssselectorMeta = bundleMetas.cssselectorMeta;
                    this.updateActiveWorkSpace(productMeta.url_product_name);
                    break;
                default:
                    break;
            }
        }
        return { productMeta, cssselectorMeta };
    }
    updateActiveWorkSpace(productname) {
        this.walkthroughConfig.workspaceConf.activeWorkspace.product_name = productname;
        window.sessionStorage["micsWalkthroughConfig"] = JSON.stringify(this.walkthroughConfig);
    }

    onEndPreview(previewMetric) {
        this.injectBuilderIfrane()
        this.builderIframeRef.addEventListener("load", () => {
            this.messenger.messageToBuilderIframe("previewModeEnd", { "metric": previewMetric });
            this.startBuilderMode();
        },
            { once: true });
    }
    validateNSetTargetElement(cssSelector, elementMeta) {
        let matchStatus = this.Util.getSelectorMatchStatus(cssSelector);
        this.targetElementData.status = matchStatus;
        this.targetElementData.selector = cssSelector;
        let newElementMeta;
        var element = null;
        switch (matchStatus) {
            case "notFound":
                this.checkTargetElementOnInterval(cssSelector);
                break;
            default:
                window.clearInterval(this.targetElementCheck.intervalId);
                element = this.Util.getElement(cssSelector, elementMeta);
                if (!this.targetElementData.childElement.selector) {
                    newElementMeta = this.customQuerySelector.getElementMeta(element, cssSelector, elementMeta);
                    this.targetElementData.elementMeta = elementMeta;
                }
                if (!this.targetElementData.childElement.selector || (this.targetElementData.childElement.selector && this.targetElementData.childElement.status != "notFound")) {
                    this.domObserver.setTargetElement(element);
                }
                else if (this.targetElementData.childElement.selector && this.targetElementData.childElement.status == "notFound") {
                    matchStatus = "notFound";
                    this.checkTargetElementOnInterval(cssSelector);
                }
        };
        if (this.targetElementData.childElement.selector && element) {
            element.contentWindow.postMessage({ action: "validateNSetTargetElement", source: "inproductsdk", origin: "inproduct_parentsdk", data: { cssselector: this.targetElementData.childElement.selector, elementMeta: elementMeta }, mode: "walkthroughbuilder" }, "*");
        }
        var selectedElementResponse = {};
        if (matchStatus == "foundUnique" || matchStatus == "foundMultiple") {
            selectedElementResponse = this.getSelectedElementResponse(this.targetElementData);
        }
        let response = { "cssSelectorMatch": matchStatus, "productMeta": selectedElementResponse.productMeta, "cssselectorMeta": selectedElementResponse.cssselectorMeta, selector: cssSelector };
        newElementMeta ? response.elementMeta = newElementMeta : "";
        this.messenger.messageToBuilderIframe(
            "cssSelectorValidated", response
        );
    }
    checkTargetElementOnInterval() {
        window.clearInterval(this.targetElementCheck.intervalId);
        let cssSelector = this.targetElementData.selector;
        this.targetElementCheck.intervalId = window.setInterval(
            () => {
                if (this.targetElementData.selector != cssSelector) window.clearInterval(this.targetElementCheck.intervalId);
                let matchStatus = this.Util.getSelectorMatchStatus(cssSelector);
                switch (matchStatus) {
                    case "notFound":
                        break;
                    default:
                        this.validateNSetTargetElement(cssSelector);
                }
            }, 1000);
    }
    updateDomChanges(updatedDimensions) {
        let matchStatus = this.Util.getSelectorMatchStatus(this.targetElementData.selector);
        switch (matchStatus) {
            case "notFound":
                this.validateNSetTargetElement(this.targetElementData.selector);
                break;
            default:
                let elementDimensions = updatedDimensions || this.Util.getElementDimensions(this.Util.getElement(this.targetElementData.selector, this.targetElementData.elementMeta));
                let isChildAvailable = this.targetElementData.childElement.selector ? true : false;
                let element = this.Util.getElement(this.targetElementData.selector, this.targetElementData.elementMeta);
                this.targetElementData.dimensions = elementDimensions;
                window.top == window && this.currentMode == "interaction" ? this.interaction.repositionInteractArea() : "";
                !isChildAvailable ? this.messenger.messageToBuilderIframe(
                    "domChangesObserved",
                    { "targetElementDimensions": elementDimensions, isChildAvailable: isChildAvailable }
                ) : element.contentWindow.postMessage({ action: "domChangesObserved", origin: "inproduct_parentsdk", source: "inproductsdk", mode: "walkthroughbuilder" }, "*");
                if (this.domObserver.getCurrentTarget() != this.Util.getElement(this.targetElementData.selector, this.targetElementData.elementMeta)) {
                    this.domObserver.setTargetElement(this.Util.getElement(this.targetElementData.selector, this.targetElementData.elementMeta));
                }
        };
    }
    triggerTargetElement() {
        let targetElement = this.Util.getElement(this.targetElementData.selector, this.targetElementData.elementMeta);
        if (this.targetElementData.childElement.selector) {
            targetElement.contentWindow.postMessage({ action: "triggerTarget", source: "inproductsdk", origin: "inproduct_parentsdk", data: {}, mode: "walkthroughbuilder" }, "*");
        }
        else {
            targetElement.dispatchEvent(this.createMouseEvent('click'));
            targetElement.dispatchEvent(this.createMouseEvent('mousedown'));
            targetElement.dispatchEvent(this.createMouseEvent('mouseup'));
        }
    }
    createMouseEvent(eventname) {
        return new MouseEvent(eventname, {
            bubbles: true,
            cancelable: true,
            view: window
        })
    }
    checkSelectorIsInCrossOrigin(cssSelector) {
        if (cssSelector.includes('|iframe.cross|')) {
            const parts = cssSelector.split('|iframe.cross|');
            return {
                isCrossOrigin: true,
                validSelector: parts[0],
                invalidSelector: parts.slice(1).join('|iframe.cross|')
            };
        }
        return {
            isCrossOrigin: false,
            validSelector: cssSelector,
            invalidSelector: null
        };
    }
    getNewCssSelector(oldSelector, selectorConf, selectorFormat, elementMeta) {
        var { isCrossOrigin, validSelector, invalidSelector } = this.checkSelectorIsInCrossOrigin(oldSelector);
        this.targetElementData.childElement.selector = invalidSelector;
        let tempElementMeta = isCrossOrigin ? {} : elementMeta;
        let element = this.Util.getElement(validSelector, tempElementMeta);
        this.cssSelector.selectorConf = selectorConf;
        let newSelector = this.customQuerySelector.constructSelector(element, selectorConf, selectorFormat);
        if (isCrossOrigin) {
            element.contentWindow.postMessage({
                action: "getNewCssSelector",
                source: "inproductsdk",
                origin: "inproduct_parentsdk",
                data: { selectorConf: selectorConf, cssselector: invalidSelector, selectorFormat: selectorFormat, elementMeta: elementMeta },
                mode: "walkthroughbuilder"
            }, "*");
            return;
        }
        var selectedElementResponse = this.getSelectedElementResponse({ selector: newSelector });
        this.targetElementData.elementMeta = this.customQuerySelector.getElementMeta(element, newSelector, elementMeta);
        this.messenger.messageToBuilderIframe(
            "updateNewCssSelector", {
            "productMeta": selectedElementResponse.productMeta,
            "cssselectorMeta": selectedElementResponse.cssselectorMeta,
            "selector": newSelector,
            "newCssSelector": newSelector,
            "selectorConf": selectorConf,
            "elementMeta": this.targetElementData.elementMeta,
        }
        );
    }
    startInteractiveMode(backdropConfig, highlighterConfig) {
        this.currentMode = "interaction";
        this.hideBuilder();
        this.interaction.startInteractionMode(this.targetElementData, backdropConfig, highlighterConfig);
    }

    endInteractiveMode() {
        this.startBuilderMode();
    }

    removeBuilder() {
        window.sessionStorage.removeItem("builder.ongoingWalkthroughMode");
        delete window.sessionStorage["micsWalkthroughConfig"];
        this.messenger.removeMessageListener();
        window.clearInterval(this.urlCheck.intervalId);
        this.domObserver.destroyDOMObservers();
        this.builderIframeRef.remove();
        this.parentContainer.destroy();
        InproductMsgListener && InproductMsgListener.listener ? InproductMsgListener.listener.closeConnection() : "";
    }
    stopDomObserversForPreviousStep() {
        this.domObserver.destroyDOMObservers();
        if (this.targetElementData.childElement.selector) {
            var elementRef = this.Util.getElement(this.targetElementData.selector);
            if (elementRef && this.targetElementData.childElement.selector && elementRef.contentWindow) {
                this.targetElementData.childElement.selector = null;
                this.targetElementData.childElement.status = "notfound";
                elementRef.contentWindow.postMessage({ action: "stopDomObserver", source: "inproductsdk", origin: "inproduct_parentsdk", mode: "walkthroughbuilder", data: {} }, "*");
            }
        }
    }

    // startPreviewFlow(walkthroughConfig) {
    //     if (!WalkthroughSDK.getInstance()) return;
    //     let flowData = JSON.parse(walkthroughConfig.flowData),
    //         walkthroughData = JSON.parse(flowData.data).layoutdata;
    //     let walkthroughJSON = {
    //         flowID: flowData.id,
    //         PID: "0",
    //         renderingMode: "preview",
    //     };
    //     this.initWalkthroughSDK(walkthroughJSON, walkthroughData);
    // }

    // initWalkthroughSDK(walkthroughJSON, walkthroughData) {
    //     window.sessionStorage.setItem("currentongoingWalkthroughDataGID", JSON.stringify(walkthroughJSON));
    //     window.sessionStorage.setItem(walkthroughJSON.flowID, JSON.stringify(walkthroughData));
    //     window.location.reload();
    // }

    // startVerifyFlow(walkthroughConfig) {
    //     if (!WalkthroughSDK.getInstance()) return;
    //     let flowData = JSON.parse(walkthroughConfig.flowData),
    //         walkthroughData = JSON.parse(flowData.data);
    //     let walkthroughJSON = {
    //         flowID: flowData.id,
    //         PID: "-1",
    //         renderingMode: "verify"
    //     };
    //     this.initWalkthroughSDK(walkthroughJSON, walkthroughData);
    // }

    startEditingFlow(walkthroughConfig) {
        this.editableFlowData = walkthroughConfig.flowdata;
        this.createBuilder(walkthroughConfig);
    }
    closeTab() {
        window.close();
    }
    setMessengerConfig() {
        if (window.top != window) {
            this.messenger.initializeIframeCommunication(window.parent, "*");
        }
    }
    sendCurrentModeToChild(ref, source) {
        if (this.currentMode == "selector") {
            var selectorConf = this.cssSelector.selectorConf;
            let selectorFormat = this.cssSelector.selectorFormat;
            InProduct_CrossOriginMessenger.instance.sendMsg(source, "selectorModeOn", "walkthroughbuilder", { selectorConf: selectorConf, selectorFormat: selectorFormat }, "inproduct_parentsdk");
            this.cssSelector.removeCrossOriginWhileSelector();
        }
        else if (this.currentMode == "preview") {
            InProduct_CrossOriginMessenger.instance.sendMsg(source, "addEventListener", "walkthroughpreview", {}, "inproduct_parentsdk");
        }
    }
    handlePostMessages(data, source) {
        switch (data.origin) {
            case "inproduct_parentsdk":
                this.handleParentSDKMessages(data, source);
                break;
            case "inproduct_childsdk":
                this.handleChildSDKMessages(data, source);
                break;
            default:
                break;
        }
    }
    handleChildSDKMessages(data, source) {
        switch (data.action) {
            case "cssSelectorModeResponse":
                this.handleSelectedElementFromChild(data, source);
                break;
            case "domChangesObserved":
                var iframeRef = InProduct_CrossOriginMessenger.instance.getMatchedIframe(source);
                var dimensions = this.calculateParentCoordinates(iframeRef, data.data.targetElementDimensions);
                this.targetElementData.dimensions = dimensions;
                this.domObserver.initialDimensions = iframeRef.getBoundingClientRect();
                data.data.targetElementDimensions = dimensions;
                window.top == window && this.currentMode == "interaction" ? this.interaction.repositionInteractArea() : "";
                this.messenger.messageToBuilderIframe('domChangesObserved', data.data);
                break;
            case "cssSelectorValidated":
                this.handleSelectedElementValidationFromChild(data, source);
                break;
            case "updateNewCssSelector":
                this.handleUpdatedCssSelector(data, source);
                break;
            default:
                break;
        }
    }
    handleParentSDKMessages(data, source) {
        switch (data.action) {
            case "selectorModeOn":
                this.handleSelectorModeOn(data, source);
                break;
            case "selectorModeOff":
                this.handleSelectorModeOff();
                break;
            case "domChangesObserved":
                this.updateDomChanges();
                break;
            case "stopDomObserver":
                this.stopDomObserversForPreviousStep();
                break;
            case "triggerTarget":
                this.triggerTargetElement();
                break;
            case "validateNSetTargetElement":
                this.setChildElement(data.data.cssselector);
                this.validateNSetTargetElement(this.targetElementData.selector, data.data.elementMeta);
                break;
            case "getNewCssSelector":
                this.getNewCssSelector(data.data.cssselector, data.data.selectorConf, data.data.selectorFormat, data.data.elementMeta);
                break;
            case "registerIframe":
                InProduct_ChildMessageInitiator.instance.sendInitMsg();
                break;
            default:
                break;
        }
    }
    handleSelectorModeOn(payload) {
        this.currentMode = "selector";
        var selectorConf = payload.data.selectorConf;
        let selectorFormat = payload.data.selectorFormat;
        (selectorConf) ? this.cssSelector.setSelectorConf(selectorConf) : null;
        this.cssSelector.setSelectorFormat(selectorFormat);
        this.cssSelector.startSelectorMode({ showInfo: false });
        InProduct_CrossOriginMessenger.instance.sendMsgToAllChild("selectorModeOn", { selectorConf: selectorConf, selectorFormat: selectorFormat }, "walkthroughbuilder");
    }
    handleSelectorModeOff() {
        this.currentMode = null;
        InProduct_CrossOriginMessenger.instance.sendMsgToAllChild("endSelectorMode", {}, "walkthroughbuilder");
        this.cssSelector.crossOriginEndSelectorMode();
    }
    handleSelectedElementFromChild(payload, source) {
        var response = payload.data.response;
        var selectedElementData = response.selectedElementData;
        this.handleSelectorModeOff();
        if (response.status == "selected") {
            var selectorConf = this.cssSelector.selectorConf;
            let selectorFormat = this.cssSelector.selectorFormat;
            var iframeRef = InProduct_CrossOriginMessenger.instance.getMatchedIframe(source);
            var iframePath = this.cssSelector.cqs.constructSelector(iframeRef, selectorConf, selectorFormat);
            var dimensions = this.calculateParentCoordinates(iframeRef, selectedElementData.dimensions);
            this.Util.scrollToTarget(iframeRef);
            this.domObserver.setTargetElement(iframeRef);
            this.targetElementData.selector = iframePath;
            this.targetElementData.childElement.selector = selectedElementData.selector;
            this.targetElementData.childElement.status = "foundUnique";
            payload.data.response.selectedElementData.dimensions = dimensions;
            payload.data.response.selectedElementData.selector = iframePath + " |iframe.cross| " + selectedElementData.selector;
            if (window.top == window) {
                var meta = this.getProductMeta(payload.data.response.selectedElementData.selector);
                payload.data.response.selectedElementData.productMeta = meta.productMeta;
                payload.data.response.selectedElementData.cssselectorMeta = meta.cssselectorMeta;
            }
        }
        window.top == window ? this.showBuilder() : "";
        this.messenger.messageToBuilderIframe('cssSelectorModeResponse', payload.data);
    }
    handleSelectedElementValidationFromChild(data, source) {
        var iframePath = this.targetElementData.selector + " |iframe.cross| ";
        data.data.selector = iframePath + data.data.selector;
        this.targetElementData.childElement.status = data.data.cssSelectorMatch;
        if (data.data.cssSelectorMatch == "notFound") {
            this.messenger.messageToBuilderIframe('cssSelectorValidated', data.data);
        }
        else {
            if (window.top == window) {
                var meta = this.getProductMeta(data.data.selector);
                data.data.productMeta = meta.productMeta;
                data.data.cssselectorMeta = meta.cssselectorMeta;
                this.messenger.messageToBuilderIframe('cssSelectorValidated', data.data);
            }
            this.messenger.messageToBuilderIframe('cssSelectorValidated', data.data);
        }
    }
    handleUpdatedCssSelector(data, source) {
        var iframeRef = InProduct_CrossOriginMessenger.instance.getMatchedIframe(source);
        var selectorConf = this.cssSelector.selectorConf;
        var iframePath = this.cssSelector.cqs.constructSelector(iframeRef, selectorConf) + " |iframe.cross| ";
        data.data.selector = iframePath + data.data.selector;
        data.data.newCssSelector = iframePath + data.data.selector;
        if (window.top == window) {
            var meta = this.getProductMeta(data.data.selector);
            data.data.productMeta = meta.productMeta;
            data.data.cssselectorMeta = meta.cssselectorMeta;
        }
        this.messenger.messageToBuilderIframe('updateNewCssSelector', data.data);
    }
    calculateParentCoordinates(iframeRef, selectedElementDimensions) {
        var getIframeIncludesdimensions = this.addIframeOffset(iframeRef, selectedElementDimensions);
        return getIframeIncludesdimensions;
    }
    addIframeOffset(iframe, dimensions) {
        const rect = iframe.getBoundingClientRect();
        const style = getComputedStyle(iframe);
        dimensions.x += rect.x + parseFloat(style.borderLeftWidth || 0);
        dimensions.y += rect.y + parseFloat(style.borderTopWidth || 0);
        dimensions.left += rect.left + parseFloat(style.borderLeftWidth || 0);
        dimensions.top += rect.top + parseFloat(style.borderTopWidth || 0);
        return dimensions;
    }
    getProductMeta(cssSelector) {
        return this.findProductBySelector(cssSelector);
    }
    handlePreviewPostMessages(data, source) {
        this.currentMode = "preview";
        if (data.origin == "inproduct_parentsdk") {
            if (data.action == "addEventListener") {
                this.setPreviewEventListeners();
            }
            else if (data.action == "removeEventListener") {
                this.currentMode = "";
                this.removeEscapeEventForPreview();
                InProduct_CrossOriginMessenger.instance.sendMsgToAllChild('removeEventListener', {}, "walkthroughpreview");
            }
        }
        else if (data.origin == "inproduct_childsdk") {
            if (data.action == "removeEventListener") {
                this.currentMode = "";
                if (window.top == window) {
                    this.builderPreview.renderingSDK.endTour();
                    this.builderPreview.endPreview();
                } else {
                    this.removeEscapeEventForPreview();
                }
                InProduct_CrossOriginMessenger.instance.sendMsgToAllChild('removeEventListener', {}, "walkthroughpreview", source);
            }
        }
    }
    setPreviewEventListeners() {
        this.builderPreview.setPreviewListenters();
    }
    removeEscapeEventForPreview() {
        this.builderPreview.removePreviewListeners();
    }
    sendEscapeEventForPreview(event) {
        if (event.key == "Escape") {
            this.currentMode = "";
            this.Util.preventEventBehaviours(event);
            InProduct_CrossOriginMessenger.instance.sendMsgToAllChild("removeEventListener", {}, "walkthroughpreview");
            window.parent.postMessage({ action: "removeEventListener", data: {}, mode: "walkthroughpreview", origin: "inproduct_childsdk", source: "inproductsdk" }, "*");
            return;
        }
    }
}
//  $Id$ 
class BundleWalkthroughUtility {
    constructor() {
        this.bundleName = "";
        this.activeWorkspace = {};
        this.childProductConf = {};
        this.cssSelector = new CssSelector(this.updateSelectedTargetElement.bind(this));
    }
    initialize(workspaceConf) {
        this.bundleName = workspaceConf.product_name;
        this.activeWorkspace = workspaceConf.activeWorkspace;
        this.childProductConf = workspaceConf.productConf;
    }
    updateSelectedTargetElement(selectedElementData) { }
    getBundleMetas(cssSelector) {
        return this.checkToolTipInWhichProduct(cssSelector);
    }
    checkToolTipInWhichProduct(cssSelector) {
        var productMeta = { url_product_name: this.bundleName, cssselector_product_name: this.bundleName };
        var cssselectorMeta = { bundle_cssselector: "", product_cssselector: cssSelector };
        var isRecentlyAccessed = this.checkRecentlyAccessedProduct();
        var isTooltipPlacedInBundle = false;
        if (isRecentlyAccessed && this.activeWorkspace.product_name != "parent") {
            productMeta.url_product_name = this.activeWorkspace.product_name;
        }
        else {
            productMeta.url_product_name = this.getUrlMatchedProductName();
        }

        let hasBaseSelectors = this.checkBaseSelectors();
        if (hasBaseSelectors) {
            isTooltipPlacedInBundle = this.isTooltipPlacedInBundlePart(cssSelector, productMeta.url_product_name);
            if (isTooltipPlacedInBundle) {
                productMeta.cssselector_product_name = "parent";
            }
            else {
                productMeta.cssselector_product_name = productMeta.url_product_name;
                cssselectorMeta = this.splitBundlePathInCssSelector(cssSelector, productMeta.cssselector_product_name);
            }
        } else {
            productMeta.cssselector_product_name = productMeta.url_product_name;
        }
        this.activeWorkspace.product_name = productMeta.url_product_name;
        return { productMeta, cssselectorMeta };
    }
    isTooltipForBundle() {
        return this.activeWorkspace.product_name == this.bundleName;
    }
    checkRecentlyAccessedProduct() {
        var url = window.location.href.replace(window.location.origin, '');;
        var productName = this.activeWorkspace.product_name == this.bundleName ? "parent" : this.activeWorkspace.product_name;
        if (productName == "parent") {
            return false;
        }
        var urlPattern = this.childProductConf[productName].producturl_regex;
        if (urlPattern && new RegExp(urlPattern).test(url)) {
            return true;
        }
        return false;
    }
    isTooltipPlacedInBundlePart(cssSelector, productName) {
        if (productName == "parent") {
            return true;
        }
        var productConf = this.childProductConf[productName];
        var productIframeRef = this.cssSelector.cqs.getElement(productConf.basecssselector_id);
        if(productConf.element_type == "crossorigin_iframe"){
            if(cssSelector.includes('|iframe.cross|')){
                var iframeRef = cssSelector.split('|iframe.cross|')[0];
                var elementRef = this.cssSelector.cqs.getElement(iframeRef);
                if(productIframeRef == elementRef) {
                    return false;
                } 
            }
            return true;
        }
        var elementRef = this.cssSelector.cqs.getElement(cssSelector);
        if (productIframeRef) {
            if (productConf.element_type == "iframe") {
                if (productIframeRef.contentDocument && productIframeRef.contentDocument.contains(elementRef)) {
                    return false;
                }
            }
            else if (productConf.element_type == "shadowDOM") {
                if (productIframeRef.shadowRoot && productIframeRef.shadowRoot.contains(elementRef)) {
                    return false;
                }
            }
            else if (productConf.element_type == "htmlelement") {
                if (productIframeRef.contains(elementRef)) {
                    return false;
                }
            }
            else {
                return true;
            }
        }
        return true;
    }
    getUrlMatchedProductName() {
        var keys = Object.keys(this.childProductConf);
        var url = window.location.href.replace(window.location.origin, '');;
        var urlPattern = "";
        for (var i = 0; i < keys.length; i++) {
            var product = keys[i];
            urlPattern = this.childProductConf[product].producturl_regex;
            if (product != this.bundleName && urlPattern && new RegExp(urlPattern).test(url)) {
                return product;
            }
        }
        return "parent";
    }
    checkRecentlyTooltipPlaced() {
        var url = this.Util.getCurrentUrl();
        var product_name = this.activeWorkspace.product_name;
        var urlPattern = new RegExp(this.childProductConf[product_name].producturl_regex);
        if (urlPattern.test(url)) {
            return true;
        }
        return false;
    }
    splitBundlePathInCssSelector(cssSelector, productName) {
        var productConf = this.childProductConf[productName];
        var productBaseSelector = this.cssSelector.cqs.getElement(
            productConf.basecssselector_id
        );
        var currentCssSelectorParts = this.getSplitIndex(cssSelector);
        var selectorPath = "";
        var selectorRef = null;
        var matchedIndex = -1;
        currentCssSelectorParts.values.some((part, index) => {
            if (index > 0) {
                selectorPath += currentCssSelectorParts.splitters[index - 1];
            }
            selectorPath += part;
            selectorRef = this.cssSelector.cqs.getElement(selectorPath);
            if (productBaseSelector.contains(selectorRef)) {
                if (productBaseSelector == selectorRef) {
                    matchedIndex = index;
                }
                return true;
            }
            return false;
        });
        currentCssSelectorParts.splitters[matchedIndex] ? selectorPath += currentCssSelectorParts.splitters[matchedIndex] : "";
        var remainingPath = "";
        for (var i = matchedIndex + 1; i < currentCssSelectorParts.values.length; i++) {
            if (remainingPath) {
                remainingPath += currentCssSelectorParts.splitters[i - 1];
            }
            remainingPath += currentCssSelectorParts.values[i];
        }
        return { bundle_cssselector: selectorPath, product_cssselector: remainingPath };
    }
    getSplitIndex(cssSelector) {
        cssSelector = cssSelector.replace(/\s*(\|iframe\.cross\||\|iframe\||\|shadowDOM\||>)\s*/g,'$1');
        let parts = cssSelector.split(/(\|iframe\.cross\||\|iframe\||\|shadowDOM\||>|[\s]+)/).filter(Boolean);
        let values = [];
        let splitters = [];
        for (let part of parts) {
            if (part === '|iframe|') {
                splitters.push('|iframe|');
            } else if (part === '|shadowDOM|') {
                splitters.push('|shadowDOM|');
            } else if (part === '>') {
                splitters.push('>');
            } 
            else if(part == "|iframe.cross|"){
                splitters.push(part);
            }else if (/^\s+$/.test(part)) {
                splitters.push(part);
            } else {
                values.push(part.trim());
            }
        }
        return { values, splitters };
    }

    checkBaseSelectors() {
        let products = Object.keys(this.childProductConf);
        for (let i = 0; i < products.length; i++) {
            let product = products[i];
            let selector = this.childProductConf[product].basecssselector_id;
            if (product != this.bundleName && selector) {
                return true;
            }
        }
        return false;
    }

}// $Id$

class InProduct_CrossOriginMessenger{
    static instance = null;
    static initialize(){
        if(!InProduct_CrossOriginMessenger.instance){
            InProduct_CrossOriginMessenger.instance = new InProduct_CrossOriginMessenger();
        }
        return InProduct_CrossOriginMessenger.instance;
    }
    constructor(){
        this.registeredIframesSource = [];
        this.registeredIframeRef = [];
        this.targetElementCallback;
    }
    addEventListeners(){
        window.addEventListener('message',(event)=>{
            if(typeof event.data == "object" &&  event.data.source == "inproductsdk"){
                switch ( event.data.mode) {
                    case "walkthroughbuilder":
                        if(WalkthroughBuilderSDK.instance){
                            WalkthroughBuilderSDK.instance.handlePostMessages(event.data,event.source);
                        }
                        break;
                    case "iframeRegistration":
                        this.handleRegistrationPostMessages(event.data,event.source);
                        break;
                    case "walkthroughrendering":
                        if (event.data.origin == "inproduct_parentsdk") {
                            InProduct_RenderingSDKMessenger.getInstance().processIframeMsg(event.data, event.source);
                        } else {
                            this.targetElementCallback ? this.targetElementCallback(event.data, event.source) : '';
                        }
                        break;
                    case "walkthroughpreview":
                        if(WalkthroughBuilderSDK.instance){
                            WalkthroughBuilderSDK.instance.handlePreviewPostMessages(event.data,event.source);
                        }                        
                        break;
                    default:
                        break;
                }
            }
        })
    }
    handleRegistrationPostMessages(payload,source){
        switch (payload.origin) {
            case "inproduct_parentsdk":
                this.handleRegistrationMsgFromParentSDK(payload,source);
                break;
            case "inproduct_childsdk":
                this.handleRegistrationMsgFromChildSDK(payload,source);
                break;
            default:
                break;
        }
    }
    handleRegistrationMsgFromParentSDK(payload,source){
        switch (payload.action) {
            case "iframeRegistedCompleted":
                this.handleRegistrationSuccess();
                break;
            default:
                break;
        }
    }
    handleRegistrationMsgFromChildSDK(payload,source){
        switch (payload.action) {
            case "iframeRegister":
                this.registerIframes(source);
                break;    
            default:
                break;
        }
    }
    handleRegistrationSuccess(){
        InProduct_ChildMessageInitiator.instance.handleRegistrationSuccess();
    }
    registerIframes(source){
        var iframeRef = this.getMatchedIframe(source);
        if(iframeRef){
            this.addNewIframes(iframeRef,source);
            this.sendMsg(source,"iframeRegistedCompleted","iframeRegistration","inproduct_parentsdk",{});
            return;   
        }
    }
    getMatchedIframe(source){
       const iframe = Array.from(document.querySelectorAll("iframe")).find(el => el.contentWindow === source);
       return iframe; 
    }
    addNewIframes(ref, source) {
        if (!this.registeredIframesSource.includes(source)) {
            this.registeredIframesSource.push(source);
            this.registeredIframeRef.push(ref);   
        }
        var builderRef = WalkthroughBuilderSDK.instance;
        builderRef ? builderRef.sendCurrentModeToChild(ref,source) : "";
    }
    sendMsg(source,action,mode,data,origin){
        source.postMessage({   
            source:"inproductsdk",
            mode:mode,
            origin :origin,
            action:action,
            data:data
        },"*")
    }
    sendMsgToAllChild(action,data,mode){
        var self = this;
        this.registeredIframesSource.forEach(source=>{
            self.sendMsg(source,action,mode,data,"inproduct_parentsdk");
        })
    }
}/*$Id$*/

//Check if ExtensionCommunicator is already declared;

if (!globalThis.ExtensionCommunicator) {

    class ExtensionCommunicator {
        static extensionID = "pdpmpoaehnemjojblnnldhhhgnlglhnb";
        static currentVersion = 2.2;
        static featureVersionMapping = {
            walkthrough: 2,
            video: 2,
            guide: 2.8,
        };
        static DapfeatureVersionMapping = {
            walkthrough: 2.1,
            video: 2.1,
            guide: 2.8,
        };
        static callbackIdcounter = 0;
        static callbackStacks = [];
        static extensionDownloadLink = "h"+"ttps://chromewebstore.google.com/detail/zoho-digital-adoption-pla/clpgadppfmgccacjjldmieljfmplinal?authuser=0&hl=en";

        static {
            try {
                window.top.addEventListener("message", (event) => {
                if (event.data.source !== "MICS_EXTENSION" || event.data.callbackid == undefined)
                    return;
                ExtensionCommunicator.callbackStacks[event.data.callbackid](event.data);
            });
            } catch (error) {
                console.log(error);
            }


            try {
                chrome.runtime.sendMessage(
                    ExtensionCommunicator.extensionID, { action: "isExtensionInstalled" },
                    (response) => {
                        if (response == undefined) {
                        } else {
                            let data = {};
                            data.version = response.version ? response.version : 1.1;
                            data.isInstalled = response.isInstalled;
                            sessionStorage["mics.extension.metadata"] = JSON.stringify(data);
                        }
                    }
                );
            } catch (error) { }
        }

        static sendMessageToExtension(data, callback) {
            const sendMessage = (response) => {
                if (!response) {
                    callback(false);
                    return;
                };
                if (response.version > 2) {
                    let callbackid = ++ExtensionCommunicator.callbackIdcounter;
                    ExtensionCommunicator.callbackStacks[callbackid] = callback;
                    data.callbackid = callbackid;
                    data.source = "MICS_SCRIPTS";
                    window.top.postMessage(data, "*");
                } else {
                    try {
                        chrome.runtime.sendMessage(ExtensionCommunicator.extensionID, data,
                            (response) => {
                                if (response == undefined) {
                                    callback(response);
                                    return;
                                } else {
                                    callback(response);
                                }
                            }
                        );
                    } catch (error) {
                        callback(false);
                    }
                }
            }

            ExtensionCommunicator.isExtensionInstalled(sendMessage);
        }

        static isExtensionInstalled(callback) {
            if (sessionStorage.getItem("mics.extension.metadata")) {
                let response = JSON.parse(sessionStorage.getItem("mics.extension.metadata"));
                //if version is lessthan or equal to 2 , send message to extension;
                if (response.version <= 2) {
                    ExtensionCommunicator.isOldExtensionInstalled(callback);
                } else {
                    callback(response);
                }
            } else {
                let writeMetaToSession = (response) => {
                    if (!response) {
                        callback(false);
                        return;
                    }
                    let data = {};
                    data.version = response.version ? response.version : 1.1;
                    data.isInstalled = response.isInstalled;
                    sessionStorage["mics.extension.metadata"] = JSON.stringify(data);
                    callback(response);
                }
                ExtensionCommunicator.isOldExtensionInstalled(writeMetaToSession);
            }
        }

        static isOldExtensionInstalled(callback) {
            try {
                chrome.runtime.sendMessage(ExtensionCommunicator.extensionID, { action: "isExtensionInstalled" },
                    (response) => {
                        if (!response) {
                            sessionStorage.removeItem("mics.extension.metadata");
                            callback(false);
                            return;
                        }
                        callback(response);
                    });
            } catch (error) {
                sessionStorage.removeItem("mics.extension.metadata");
                callback(false);
            }
        }
    }

    globalThis.ExtensionCommunicator = ExtensionCommunicator;
} else {
    //ExtensionCommunicator Class is already defined
}
//$Id$
class WalkthroughBaseParser{
    constructor(){
        this.CSS_SELECTOR_ENUM ={
            iframe: "|iframe|",
            shadowDOM: "|shadowDOM|",
            crossorigin_iframe:"|iframe.cross|",
            htmlelement: " ", // base element is htmlelement
            "": "", // for no base element
        }
    }

    parseCss(walkthroughdata,workspaceconf){
        //for old rendering json 
        if(walkthroughdata.version == undefined || walkthroughdata.version<=3){
            return walkthroughdata;
        }
        //for new rendering json 
        else if(walkthroughdata.version>3&&workspaceconf?.product_type=='bundle'){
            for(let i =0;i<walkthroughdata.templates.length;i++){
                let productMeta =  walkthroughdata.templates[i].productMeta;
                if (!productMeta?.cssselector_product_name || productMeta.cssselector_product_name=="parent") {
                continue;
                }
                let cssselector_product_name = productMeta.cssselector_product_name;
    
                let baseCssSelectorId = workspaceconf.productConf[cssselector_product_name].basecssselector_id;
                let baseelementtype = this.CSS_SELECTOR_ENUM[workspaceconf.productConf[cssselector_product_name].element_type];
                let productCssSelectorId =  walkthroughdata.templates[i].meta.targetelementID;
    
               //baseCssSelectorId  +  baseelementtype  +  productCssSelectorId;
                walkthroughdata.templates[i].meta.targetelementID = baseCssSelectorId + baseelementtype + productCssSelectorId;
            }
        }
        


        return walkthroughdata;
    }

    parseURL(walkthroughdata,workspaceconf,dynamicPath){
        let currenturl = walkthroughdata.templates[0].meta.layoutroute;
        let pageCollection = new PageCollection(); 
        //for mics
        if(walkthroughdata.scope == "Service"){
            return WalkthroughUtility.constructDynamicURL(currenturl,dynamicPath);
        }
        //for dap
        else if(walkthroughdata.scope=='Enterprise'){
            let url = walkthroughdata.templates[0].meta.layoutroute;
            var productname = walkthroughdata.templates[0].productMeta?.url_product_name;
            return pageCollection.constructUrlPathUsingWorkspaceConf(workspaceconf,url,productname);
           }
    }


   constructURL(urlformat,urlconf){
    let urlKeyvsVauleMap = this.getURLKeyvsValueMap(urlconf);
    return WalkthroughUtility.constructDynamicURL(urlformat,urlKeyvsVauleMap);
   }

  getURLKeyvsValueMap(walkthroughconfig) {
      if (!walkthroughconfig.urlDynamicIdConf) return {};
      let IDvsValue = {};
      
      let dynamicConfig = JSON.parse(JSON.stringify(walkthroughconfig));
      
      dynamicConfig.urlDynamicIdConf = JSON.parse(dynamicConfig.urlDynamicIdConf);
      dynamicConfig.urlDynamicIdConf.forEach((data) => {
            IDvsValue[data.dynamicId] = data.properties.value;
      });
      return IDvsValue;
 }


}//  $Id$
class WalkthroughLayoutManager {
    static instance = ''
    constructor() {
        this.ongoingStepLayout = '';   
        this.ongoingWalkthroughData='';
        this.ongoingStepData='';
        this.shadowdom='';
    }

    createLayout(shadowdom,ongoingWalkthroughData,callbackfunction){
        this.ongoingWalkthroughData=ongoingWalkthroughData;
        this.shadowdom=shadowdom;
        this.ongoingStepLayout = document.createElement('div');
        this.ongoingStepLayout.setAttribute("id", "walkthroughlayout");
        this.ongoingStepLayout.style.zIndex = 23657675643;
        this.ongoingStepLayout.style.position = "absolute";     
        shadowdom.shadowRoot.append(this.ongoingStepLayout);

        this.importCommonScript(callbackfunction);

        var style = document.createElement('style')
        style.innerHTML =ongoingWalkthroughData.commonCss;
        shadowdom.shadowRoot.append(style);

        this.addLayoutEventListener();
    }


    showStep(sdkinstance,ongoingStepData,targetElement) {
        this.ongoingStepData=ongoingStepData;
        // let ongoingStepCssSelector = ongoingStepData.meta.targetelementID;
        // // let targetElement= WalkthroughUtility.getElement(ongoingStepCssSelector);
        // // targetElement.scrollIntoView({
        // //     block: "center",
        // //     inline: "nearest"
        // // });
        this.ongoingStepLayout.innerHTML = `<style>${ongoingStepData.css}</style>`+ongoingStepData.html;
        
        this.importStepScript(sdkinstance);

       this.addEventsForCurrentStep(sdkinstance,targetElement);

    }

    hideStep(){
        let backdrop = this.ongoingStepLayout.querySelector('.backdrop_root.Overlay');
        let layout =this.ongoingStepLayout.querySelector('[id^="layoutContainer"');
        if(backdrop){
            backdrop.querySelector('#element').style.outline="none";
            backdrop.querySelector('#element').setAttribute('class','backdropBox'); 
            backdrop.querySelector('#element').style.borderRadius="0px";
            backdrop.style.pointerEvents="none";
        }
        layout?layout.style.display="none":"";
    }


    importCommonScript(callbackfunction){
       var version = this.ongoingWalkthroughData.version;

        if(version == undefined || version <= 3) {

            var commonscript = document.createElement('script');
            commonscript.innerHTML = this.ongoingWalkthroughData.commonScript;
            this.shadowdom.shadowRoot.append(commonscript);
            callbackfunction();

        } else if(version > 3) {
            var commonscript = document.createElement('script');
            commonscript.src = this.ongoingWalkthroughData.commonScriptSrc;
            commonscript.onload=()=>{callbackfunction();}
            this.shadowdom.shadowRoot.append(commonscript);
        }
    }
    importStepScript(sdkinstance){
        var version = this.ongoingWalkthroughData.version;

        if(version==undefined || version<=3)
        {
            var script=document.createElement('script');
            script.innerHTML=this.ongoingStepData.script;
            this.ongoingStepLayout.append(script);
        }
        else if(version>3){
            try {
                loadScript(sdkinstance);
            } catch (error) {
                
            }
        }
    }
    addLayoutEventListener() {
        // Adding event listener to stop propagation
        var stopBubbleEvents = ['click', 'mousedown', 'mouseup'];
        var self = this;
        stopBubbleEvents.forEach((event_type) => {
            self.ongoingStepLayout.addEventListener(event_type, (event) => {
                event.stopPropagation();
            });
        });

    }
    hideBackdrop() {
        let backdrop = this.ongoingStepLayout.querySelector('.backdrop_root');
        backdrop ? backdrop.style.display = "none" : "";
    }
    addEventsForCurrentStep(sdkinstance,targetElement){
        var buttons = this.ongoingStepLayout.querySelectorAll("#buttoncontainer");
        if (buttons) {
            buttons.forEach((buttoncontainer) => {
                var action = buttoncontainer.getAttribute('goto_action');
                var button = buttoncontainer.querySelector('button');
                //for redirecting url
                switch (action) {
                    case 'web url':
                        button.addEventListener('click', () => {
                            window.open(buttoncontainer.getAttribute('goto_action_value'), '_blank');
                        })
                        break;

                    case "NextStep":
                        button.addEventListener('click', (e) => {    
                            if (this.ongoingStepLayout.querySelectorAll('div [trigger_targetelement="true"')[0]) {
                              targetElement.click((e)=>sdkinstance.navigateToNextStep(e));
                            }
                            else{
                                sdkinstance.navigateToNextStep(e);
                            }
                            
                        })
                        break;

                    case "PreviousStep":
                        button.addEventListener('click', () => {
                            sdkinstance.navigateToPrevStep();
                        })
                        break;

                    case "Quit":
                        button.addEventListener('click', () => {
                            sdkinstance.sendMetric({
                                'statusCode': 3
                            });
                            sdkinstance.endTour();
                        })


                }
            })
        }
    }





}
//  $Id$
class WalkthroughUtility {
    static CSS_SELECTOR_ENUM = {
        iframe: " |iframe| ",
        shadowDOM: " |shadowDOM| ",
        html_element: "  "

    };
    static debugLog = [];
    static logLimit = 300;
    static showlog =false;
    static cqs = new CustomQuerySelector();
    constructor() {
    }

    static constructDynamicURL(flowurl, dynamicPath) {
        var regenaratorUrl = flowurl;
        var dynamicPatterns = flowurl.match(/{{(.*?)}}/g);
        if (dynamicPatterns) {
            dynamicPatterns = dynamicPatterns.map(value => value.slice(2, -2));
            dynamicPatterns.forEach(key => {
               regenaratorUrl = regenaratorUrl.replace(`{{${key}}}`, dynamicPath[key]);
            });
        }
        return regenaratorUrl;
    }

    static findElement(cssID) {
        var element = WalkthroughUtility.getElement(cssID)
        if (element != null && !WalkthroughUtility.isElementHidden(element)) {
            return true;
        }
        return false;
    }

    static getElementDOMObject(cssID) {
        return document.querySelector(cssID);
    }

    static logger(message, type) {
        this.debugLog.push({ "type": type, "message": message });
        this.debugLog.length > this.logLimit && this.debugLog.shift();
        if (!this.showlog) return;
        switch (type) {
            case 'log':
                console.log(message)
                break

            case 'group':
                console.group(message)
                break

            case 'groupEnd':
                console.groupEnd(message)
                break

            case 'warn':
                console.warn(message)
                break

            default:
                console.log(message)
        }
    }

    static getCurrentUrlPath() {
        return window.location.href.replace(window.location.origin, '');
    }

    static removeRegexpattern(url) {
        return url.split('/*')[0];
    }

    static urlCheck(stepurl,isWildCardMatch) {
        // if (stepurl.includes('*') && (sdkInstance.WalkthroughValidator.urlPatternCheck || !stepurl.includes('{{'))) {
        //     return WalkthroughUtility.isUrlPatternMatch(WalkthroughUtility.getCurrentUrlPath(), stepurl);
        // }
        if (WalkthroughUtility.isUrlPatternMatch(WalkthroughUtility.getCurrentUrlPath(), stepurl,isWildCardMatch)) {
            return true;
        }
        return false;
    }

    static isUrlPatternMatch(url, url_w_pattern,isWildCardMatch=false) {
        const urlUtil = WalkthroughSDK.getInstance().urlUtil;

        if(isWildCardMatch){
            return urlUtil.doesUrlWildcardPatternMatch(url, url_w_pattern);
        }
        else if (urlUtil.doesUrlEndsWithPattern) {
            return urlUtil.doesUrlEndsWithPattern(url, url_w_pattern);
        } 
        else {
            return urlUtil.doesUrlPatternMatch(url, url_w_pattern);
        }

    }

    static validateDynamicURLSyntax(url) {
        let istrue = true,
            counter = 0;
        while (counter < 100) {
            let leftBraceIndx = url.search("{{");
            let rightBraceIndx = url.search("}}");
            //console.log("SYNTAX check: sliced url" + url);
            if (leftBraceIndx > -1 && rightBraceIndx > -1 && WalkthroughUtility.validateVariableName(url.substring(leftBraceIndx + 2, rightBraceIndx))) {
                url = url.slice(rightBraceIndx + 2, url.length);
                //console.log("SYNTAX check: sliced url" + url);
            } else if (leftBraceIndx == -1 && rightBraceIndx == -1) {
                return true;
            } else {
                return false;
            }
            counter++;
        }
    }

    static validateVariableName(name) {
        return name.match("^[^a-zA-Z_$]|[^\\w$]") == null;
    }

    static getElement(selector) {
        return WalkthroughUtility.cqs.getElement(selector);
    }

    static isElementHidden(element, targetScrollCounter, iframeScrollCounter) {
        // Ensure target is visible and not covered by another element
        try {
            if (!element || !element.isConnected || !element.ownerDocument.defaultView) {
                return true;
            }
            const view = element.ownerDocument.defaultView;
            const style = view.getComputedStyle(element);

            if (WalkthroughUtility.isHiddenByStyle(style)) {
                return true;
            }

            const rect = element.getBoundingClientRect();
            if (rect.width <= 0 && rect.height <= 0) return true;

            if (targetScrollCounter && targetScrollCounter.count < targetScrollCounter.limit) {
                targetScrollCounter.count++;
                WalkthroughUtility.scrollToTarget(element);
            }

            if (rect.left+rect.width <= 0 || rect.top+rect.height <= 0 ||
                rect.top >= view.innerHeight || rect.left >= view.innerWidth
            ) {
                return false;
            } 

            const x = Math.max(0, Math.min(rect.left + rect.width / 2, view.innerWidth - 1));
            const y = Math.max(0, Math.min(rect.top + rect.height / 2, view.innerHeight - 1));

            const topElement = new CustomQuerySelector().getElementFromPoint({ x: x, y: y }, element.ownerDocument);

            if (!topElement || WalkthroughUtility.isWalkthroughElement(topElement)) {
                return false;
            }

            if (topElement === element || element.contains(topElement) || topElement.contains(element)) {
                return view.frameElement
                    ? this.isElementHidden(view.frameElement, iframeScrollCounter, iframeScrollCounter)
                    : false;
            }

            return true;
            
        } catch (error) {
            WalkthroughUtility.logger( "Walkthrough Error: Element hidden check failed\n" + error , "error");
            return false;
        }
    }

    static isHiddenByStyle(style) {
        return style.display === 'none' || style.visibility === 'hidden' ||
            style.visibility === 'collapse' || parseFloat(style.opacity) === 0;
    }

    static isWalkthroughElement(node) {
        if (!(node instanceof Element)) return false;

        if (node.id?.startsWith('walkthrough') || node.tagName?.toLowerCase().startsWith('walkthrough')) {
            return true;
        }

        return Boolean(node.closest('walkthrough-builder') ||
            document.querySelector('walkthrough-builder#walkthrough')?.shadowRoot?.contains(node)
        );
    }


    static scrollToTarget(targetElement, behavior = "smooth") {
        targetElement.scrollIntoView({ behavior: behavior, block: "center", inline: "nearest" });
    }
    
    static offsetByFrameDimensions(elementDimension, dimensionsArr) {
        dimensionsArr.forEach(dim => {
            elementDimension.x += dim.x;
            elementDimension.y += dim.y;
            elementDimension.top += dim.top;
            elementDimension.left += dim.left;
        });
        return elementDimension;
    }

}//  $Id$ 
class WalkthroughValidator {
    constructor() {
        this.urlPatternCheck = false;
    }
    postRenderValidationInterval(stepurl, targetElement,isWildCardMatch) {

        let flag = -1;
        let urlValidation = WalkthroughUtility.urlCheck(stepurl,isWildCardMatch);
        if (urlValidation == true) {
            // WalkthroughUtility.logger("url check passed");
            // var elementValidation;
            // try {
            //     elementValidation = targetElement.validate();
            // } catch (error) {
            //     elementValidation = false;
            // }

             if (targetElement.validate() && targetElement.isVisible()) {
                flag = -1;
                // WalkthroughUtility.logger("element check passed");
            } else {
                flag = 2;
                // WalkthroughUtility.logger("VALIDATION FAILED,Element not found,....")
                console.groupEnd();
            }

        } else {
            flag = 1;
            // WalkthroughUtility.logger("VALIDATION FAILED,USER NAVIGATED!......")
        }
        return flag;

    }

    preRenderValidationInterval(stepurl, targetElement,isWildCardMatch) {
        let flag = -1;
        let urlValidation = WalkthroughUtility.urlCheck(stepurl,isWildCardMatch);
        if (urlValidation == true) {
            // WalkthroughUtility.logger("url check passed");
            // let elementValidation;
            // try {
            //     elementValidation = targetElement.validate();
            // } catch (error) {
            //     flag = 2;
            // }
            if (targetElement.validate() && targetElement.isVisible()) {
                WalkthroughUtility.logger("Element found");
                WalkthroughUtility.logger("VALIDATION BEFORE RENDER SUCCESSFUL.....");
                console.groupEnd()
            } else {
                // WalkthroughUtility.logger("element check failed");
                flag = 2;
            }
        } else {
            // WalkthroughUtility.logger("url check failed");
            flag = 1;
        }
        return flag;
    }

}//  $Id$
class WalkthroughDataManager {
    constructor(serviceId, orgID) {
        this.serviceId = serviceId;
        this.orgID = orgID;
        this.dataThreshold = 20;
        this.WalkthroughData = {}
    }


    removeExistingFlowID(flowlist) {
        flowlist = flowlist.splice(0, this.dataThreshold);
        let newflowlist = []
        for (let flowid of flowlist) {
    
            if (!this.WalkthroughData[flowid]) {
                newflowlist.push(flowid)
            } else {
                this.WalkthroughData[flowid].expiryTime = new Date().getTime() + 900000
            }
        }
        return newflowlist;

    }

    optimizeData(flowlist) {
        WalkthroughUtility.logger('incoming flowlist', flowlist)
        //remove Expired Flows
        this.removeExpiredFlows()
        WalkthroughUtility.logger('after removing expried flows', this.WalkthroughData)
        let newflowlist = this.removeExistingFlowID(flowlist);
        WalkthroughUtility.logger('after removing repeated flowids', newflowlist);
        let newFlowListlen = newflowlist.length;
        let existingFlowLen = Object.keys(this.WalkthroughData).length


        //if  incoming flow list plus already present data is > greater than threshold ,remove old flows
        if (existingFlowLen + newFlowListlen >= this.dataThreshold) {
            let noofflowsToBeRemoved = Object.keys(this.WalkthroughData).length + newFlowListlen - this.dataThreshold
            this.removeAboutToExpiryFlows(noofflowsToBeRemoved)
        }

        return newflowlist;

    }

    loadFlow(flowlist,scope) {
        let self = this;

        let newflowlist = this.optimizeData(flowlist);
        if (newflowlist.length == 0) {
            return;
        }

        function onsuccess(response) {
            let data = JSON.parse(response);
            self.setwalkthroughData(data,scope);
        }

        function onerror() {
            WalkthroughUtility.logger(response);
        }
        var payload = {
            'serviceid': this.serviceId,
            'action': "load",
            "orgid":this.orgID,
            "flowidlist": newflowlist,
            "Scope":scope,
        };
        // isBundle?payload["isbundle"]=true:"";
        WalkthroughSDK.getInstance().micssdktoserver.getContent(payload, "post", onsuccess, onerror)
    }

    removeExpiredFlows() {
        let currTime = new Date().getTime();
        for (var flow in this.WalkthroughData) {
            let flowexpiryTime = this.WalkthroughData[flow].expiryTime
            if (flowexpiryTime < currTime) {
                delete(this.WalkthroughData[flow])
            }
        }
    }

    setwalkthroughData(data,scope){
        for (let flowid in data) {
            this.WalkthroughData[flowid] =data[flowid];
            this.WalkthroughData[flowid].expiryTime = new Date().getTime() + 900000;
            this.WalkthroughData[flowid].scope=scope;
            this.WalkthroughData[flowid].orgID= data[flowid].orgid ? data[flowid].orgid : this.orgID;
        }
    }

    removeAboutToExpiryFlows(count) {
        var sortedFlow = Object.entries(this.WalkthroughData).sort(this.compareObj);
        //delete topmost flows which has expiry time 
        for (var i = count; i > 0; i--) {
            WalkthroughUtility.logger("deleting about to expiry flows", sortedFlow[i])
            delete(this.WalkthroughData[sortedFlow[i]])
        }

    }



    loadAndTriggerFlow(flowid, medium, PID,scope) {
        let self = this;
        function onsuccess(response) {
            let data = JSON.parse(response)
            self.setwalkthroughData(data,scope)
            WalkthroughSDK.getInstance().triggerFlow(flowid, medium, PID,scope);
        }

        function onerror() {
            WalkthroughUtility.logger(response)
        }
        var payload = {
           'serviceid': this.serviceId,
           'action': "load",
           "orgid":this.orgID,
           "flowidlist": flowid,
           "Scope":scope,
        };
        // isBundle?payload["isbundle"]=true:"";
        WalkthroughSDK.getInstance().micssdktoserver.getContent(payload, "post", onsuccess, onerror)


    }


}//  $Id$
class WalkthroughSDK {
    static instance = null;
    constructor(serviceconf, orgid, dynamicPath) {
        //Updated CDN 2.
        this.version=2;
        this.dynamicPath = sessionStorage.getItem('dynamicPath') ? JSON.parse(sessionStorage.getItem('dynamicPath')) : {};
        this.setDynamicPath(dynamicPath);
        this.serviceid = serviceconf.serviceid;
        this.orgid = orgid;
        this.inproductconf = serviceconf;
        this.tipdomain = serviceconf.inproductdomain
        this.shadowdom = null;
        this.ongoingWalkthroughData = "";
        this.ongoingStepElement = "";
        this.ongoingStepJSON = "";
        this.ongoingStepNumber;
        this.sessionStartTime;
        this.targetElement;
        this.rePositionLayoutOnResizeref;
        this.rePositionLayoutOnScrollref;
        this.debugger = false;
        this.urlValidationConf = null;
        this.counter;
        this.flowID;
        this.urlcounter;
        this.isFlowStarted = false;
        this.prevalidationIntervalID = "";
        this.postvalidationIntervalID = "";
        this.urlUtil = new PageCollection();
        this.micssdktoserver = Micssdktoserver.getinstance(this.inproductconf, this.orgid, "walkthrough");
        this.datamanager = new WalkthroughDataManager(this.serviceid, this.orgid);
        this.WalkthroughValidator = new WalkthroughValidator();
        this.bundleParser = new WalkthroughBaseParser();
        this.WalkthroughLayoutManager = '';
        this.postmessagelistener = InproductMsgListener.initialiseListener(serviceconf , orgid);
        this.conditionBasedRenderingCallback=null;
        this.workspaceconf = {};
        this.alwaysOpenInNewTab = false;
        this.alwaysStartInCurrentTab =false;
        this.targetScrollCounter = { count: 0, limit: 4 };
        this.metricCallback=null;
        this.isWildCardMatch=false;
        this.seti18walkthrough= null;
        this.alertcallback = null;
        if (!WalkthroughSDK.instance || (this instanceof WalkthroughWrapper)) {
            WalkthroughSDK.instance = this;
        }
    }
    initialize() {
        // this.setworkspaceconf(sessionStorage.getItem("micsworkspaceconf") || {});
        this.checkActiveFlow() ? this.startTour(this.ongoingWalkthroughData) : '';
        if (sessionStorage.getItem("walkthroughsdkdata")) {
            var parsedverifydata = JSON.parse(sessionStorage.getItem("walkthroughsdkdata"));
            switch (parsedverifydata.action) {
                case "smarttour":
                    if (parsedverifydata.hasDynamicConf) {
                        this.setDynamicConf(parsedverifydata.walkthroughconf);
                        parsedverifydata.workspaceConf ? this.setworkspaceconf(parsedverifydata.workspaceConf):"";
                    }
                    this.startsmarttour(parsedverifydata);
                    break;
                case "payload":
                    break;
                default:
                    this.setverifydata(parsedverifydata);
                    break;
            }
            sessionStorage.removeItem("walkthroughsdkdata");
        };
    };

    static getInstance() {
        return WalkthroughSDK.instance;
    }
    setverifydata(message) {
        this.flowID = message.materialid
        this.promotionId = message.pid
        this.datamanager.setwalkthroughData(message.data, message.scope);
        this.ongoingWalkthroughData = message.data[message.materialid];
        this.startTour()
    }

    seti18n(i18nfunc){
        this.seti18walkthrough=i18nfunc;
    }

    setalert(alertcallback){
        /**
         * Set the alert callback. The callback must return a boolean (true/false).
         * @param {function} alertcallback - function that returns boolean
         */
        this.alertcallback = alertcallback;
    }            

    starttourbyurl(fileurl) {
        var self = this;
        var logger = InproductLogger.getInstance();
        var httpcallforjson = new InproductHttpCall('get', '', [], [], true, fileurl);
        function onsuccess(xhttp) {
            try {
                var walkthroughdataaspayload = JSON.parse(xhttp.response);
                if(self.seti18walkthrough){
                var walkthroughlanguagegetter=document.createElement("div");
                walkthroughlanguagegetter.id="walkthroughlanguagegetter";
                var walkthroughdataaspayloadcopy = JSON.parse(JSON.stringify(walkthroughdataaspayload));
                var keysinpayloaddata =Object.keys(walkthroughdataaspayloadcopy.data)[0];
                var templates = walkthroughdataaspayloadcopy.data[keysinpayloaddata].templates;
                for(let i=0; i<templates.length; i++){
                let div = document.createElement("div");
                div.innerHTML = templates[i].html;
                let nodes = div.querySelectorAll("*");
                nodes.forEach((el) => {
                    let txt = el.textContent.trim();
                    if(txt && txt !== "&nbsp;" && txt === el.innerHTML.trim()){
                        el.textContent = self.seti18walkthrough(txt);
                    }
                });
                walkthroughdataaspayloadcopy.data[keysinpayloaddata].templates[i].html = div.innerHTML;
                walkthroughlanguagegetter.appendChild(div);
            }
                walkthroughdataaspayload= JSON.parse(JSON.stringify(walkthroughdataaspayloadcopy));
            }
                self.startsmarttour(walkthroughdataaspayload, true);
            }
            catch (error) {
                logger.log("URLprovidedbyteam", "medium", "Wrong json location");
            }
        }
        function onerror(xhttp) {

        }
        httpcallforjson.makeHttpRequest(onsuccess, onerror);
    }

    startsmarttour(walkthroughconf, loadURL = false) {
        // if(!sessionStorage.getItem("currentongoingWalkthroughDataGID")) return;
        this.flowID = Object.keys(walkthroughconf.data)[0];
	this.promotionId = ((walkthroughconf.pid==='payload' && walkthroughconf.scope ===" Service")? '-20' : walkthroughconf.pid);
        this.datamanager.setwalkthroughData(walkthroughconf.data, walkthroughconf.scope);
        this.ongoingWalkthroughData = walkthroughconf.data[this.flowID];
        loadURL? this.loadTargetURL(walkthroughconf) : this.startTour();
    }

    loadTargetURL(walkthroughconf) {
        this.ongoingStepNumber = 0;
        let flowstartingURL = this.constructPath(this.ongoingWalkthroughData.templates[0].meta.layoutroute);

        let walkthroughdata = {
            flowID: this.flowID,
            PID: this.promotionId,
            scope: walkthroughconf.scope,
            orgid: this.orgid
        };
        //If user is on same url,start tour;
        if (WalkthroughUtility.urlCheck(flowstartingURL,this.isWildCardMatch) || this.alwaysStartInCurrentTab) {
            this.startTour();
            return;
        }
        //If "#" is present in url,route to page & start tour;
        else if (flowstartingURL.includes('#')) {
            flowstartingURL = window.location.origin + this.constructPath(this.ongoingWalkthroughData.templates[0].meta.layoutroute, true);
            window.location.href = WalkthroughUtility.removeRegexpattern(flowstartingURL);
            sessionStorage.setItem("currentongoingWalkthroughDataGID", JSON.stringify(walkthroughdata));
            sessionStorage.setItem(walkthroughdata.flowID, JSON.stringify(this.ongoingWalkthroughData));
            this.startTour();
            return;
        };

        sessionStorage.setItem("currentongoingWalkthroughDataGID", JSON.stringify(walkthroughdata));
        sessionStorage.setItem(walkthroughdata.flowID, JSON.stringify(this.ongoingWalkthroughData));
        //Reload page and start tour;
        flowstartingURL = window.location.origin + this.constructPath(this.ongoingWalkthroughData.templates[0].meta.layoutroute, true);
        window.location.href = WalkthroughUtility.removeRegexpattern(flowstartingURL);
    }

    createShadowDom(callbackfunction) {
        this.shadowdom = document.createElement('walkthrough-builder');
        this.shadowdom.setAttribute("id", "walkthrough");
        document.body.append(this.shadowdom)

        this.shadowdom.attachShadow({
            mode: "open"
        })
        this.WalkthroughLayoutManager = new WalkthroughLayoutManager();
        this.WalkthroughLayoutManager.createLayout(this.shadowdom, this.ongoingWalkthroughData, callbackfunction);
    }

    startTour() {
        this.parseWalkthroughData();
        if (this.isFlowStarted) return;
        WalkthroughUtility.logger("starting the tour");
        this.ongoingStepNumber = 0;
        this.targetScrollCounter.count = 0;
        this.ongoingStepData = this.ongoingWalkthroughData.templates[this.ongoingStepNumber];
        this.isFlowStarted = true;
        WalkthroughUtility.logger(`VALIDATING STEP ${this.ongoingStepNumber + 1} .....`, 'group');
        this.sessionStartTime = new Date().getTime();
        this.WalkthroughValidator.urlPatternCheck = (this.promotionId == "-1" || this.promotionId == "0") ? true : false;

        var self = this;
        function callbackfunction() {
            self.validationBeforeRender();
        };
        this.createShadowDom(callbackfunction);
    }


    navigateToNextStep(event) {
        this.targetElement.clear();
        WalkthroughUtility.logger('triggering next flow');
        this.targetScrollCounter.count = 0;
        this.sendMetric({
            'statusCode': 2
        });
        this.WalkthroughLayoutManager.hideStep();
        if (this.postvalidationIntervalID) {
            window.clearInterval(this.postvalidationIntervalID);
        }
        // this.WalkthroughLayoutManager.destroyEvents('all');
        if (this.ongoingWalkthroughData.templates.length - 1 == this.ongoingStepNumber) {
            this.sendMetric({'statusCode': 10});
            this.endTour();
            return;
        };
      
        this.ongoingStepNumber++
        this.validateAndshowStep(this.ongoingStepNumber,"next");
    }


    navigateToPrevStep() {
        this.targetElement.clear();
        this.WalkthroughLayoutManager.hideStep()
        WalkthroughUtility.logger('user navigated to previous step');
        if (this.postvalidationIntervalID) {
            window.clearInterval(this.postvalidationIntervalID);
        }
        this.ongoingStepNumber--;
        this.validateAndshowStep(this.ongoingStepNumber,"previous")
    }
   
    validateAndshowStep(stepnumber, direction) {
        WalkthroughUtility.logger(`VALIDATING STEP ${stepnumber + 1} .....`, 'group')
        this.ongoingStepData = this.ongoingWalkthroughData.templates[stepnumber];

        if (this.ongoingStepData.hasConditionBasedRendering&&this.conditionBasedRenderingCallback) {
            this.conditionBasedRenderingCallback(this.ongoingStepData,(response) => {
                switch (response.status) {
                    case "show":
                        this.validationBeforeRender();
                        break;
                    case "skip": 
                        if (direction === "next") {
                            this.ongoingStepNumber++;
                        } else if (direction === "previous") {
                            this.ongoingStepNumber--;
                        }
                        
                        if (this.ongoingStepNumber < 0 || this.ongoingStepNumber >= this.ongoingWalkthroughData.templates.length) {
                            this.endTour();
                            return;
                        }
                        this.validateAndshowStep(this.ongoingStepNumber, direction);
                        break;
                    default:
                        break;
                }
            });
        } else {
            this.validationBeforeRender();
        }
    }

    showStep() {
        this.WalkthroughLayoutManager.showStep(this,this.ongoingStepData,this.targetElement);
        // this.findLayoutposition()
        this.validationAfterRender();
    }
    clearValidationInterval() {
        this.postvalidationIntervalID ? window.clearInterval(this.postvalidationIntervalID) : " "
        this.prevalidationIntervalID ? window.clearInterval(this.prevalidationIntervalID) : " "

    }

    endTour() {
        this.targetElement ? this.targetElement.clear() : '';
        this.WalkthroughValidator.urlPatternCheck = true;
        this.clearValidationInterval();
        var isCompleted = this.ongoingWalkthroughData && this.ongoingWalkthroughData.templates && (this.ongoingWalkthroughData.templates.length - 1 == this.ongoingStepNumber);
        (this.promotionId == "-1" || this.promotionId == "0") ? (isCompleted ? this.sendVerificationStatus("success") : this.sendVerificationStatus("failed")) : '';
        if (isCompleted && typeof selfhelpsdk !== 'undefined' && selfhelpsdk.instance) {
            selfhelpsdk.instance.onContentClose('walkthrough', this.flowID);
        }
        this.ongoingWalkthroughData = '';
        this.isFlowStarted = false;
        this.ongoingStepNumber = 0;
        this.shadowdom?this.shadowdom.remove():"";
        this.resetStartTourOnSamePage();
        WalkthroughUtility.logger("Ending Tour");
        window.sessionStorage.removeItem("currentongoingWalkthroughDataGID");
        window.removeEventListener("resize", this.rePositionLayoutonResizeref);
        window.removeEventListener("wheel", this.rePositionLayoutonScrollref);
    }


    checkActiveFlow() {
        //for messageboard trigger and banner
        var currentFlowInfo = window.sessionStorage.getItem("currentongoingWalkthroughDataGID");
        if (currentFlowInfo == null) return false;
        let data = JSON.parse(currentFlowInfo);
        let flowid = data.flowID
        this.promotionId = data.PID
        this.flowID = flowid
        if ((this.orgid != data.orgid)) return false;
        this.ongoingWalkthroughData = JSON.parse(window.sessionStorage.getItem(data.flowID));
        let ongoingwalkthrough = {};
        ongoingwalkthrough[data.flowID] = this.ongoingWalkthroughData;
        this.datamanager.setwalkthroughData(ongoingwalkthrough, data.scope);
        return true;
    }

    setDynamicPath(dynamicPath) {
        for (let key in dynamicPath) {
            this.dynamicPath[key] = dynamicPath[key]
        }
        sessionStorage.setItem("dynamicPath", JSON.stringify(this.dynamicPath));
    }

    setDynamicConf(walkthroughconfig) {
        if (!walkthroughconfig.urlDynamicIdConf) return;

        walkthroughconfig.urlDynamicIdConf.forEach((data) => {
            let IDvsValue = {};
            IDvsValue[data.dynamicId] = data.properties.value;
            this.setDynamicPath(IDvsValue);
        });
    }
    setworkspaceconf(conf) {
        this.workspaceconf = conf;
        Inproductutility.setDapProductType(this.getProductType());
    }

    getProductType() {
        let type = this.workspaceconf?.product_type;
        return type ? type : "";
    }
    validationAfterRender() {
        var self = this;
        this.counter = 0;
        var urlcounter = 0;
        this.clearValidationInterval()
        var cssId = this.ongoingStepData.meta.targetelementID;
        var iscrossoriginelement =  this.targetElement.isCrossOrigin;
        var stepurl = this.ongoingStepData.meta.layoutroute;
        //let ongoingStepElement = WalkthroughUtility.getElement(cssId)
        stepurl = this.getStepUrl(stepurl);
        this.postvalidationIntervalID = window.setInterval(() => {
            stepurl = self.getStepUrl(stepurl);
            self.counter++;
            let result = self.WalkthroughValidator.postRenderValidationInterval(stepurl, self.targetElement,self.isWildCardMatch);
            switch (result) {
                case -1:
                    if (self.counter > 60) {
                        // Use alertcallback if defined, otherwise fallback to window.confirm
                        var state = true;
                        if (typeof this.alertcallback === 'function') {
                            state = !!+this.alertcallback(); // Ensure boolean
                        } else {
                            state = window.confirm("Do you want to quit the flow?");
                        }
                        if (state) {
                            window.clearInterval(self.postvalidationIntervalID);
                            self.sendMetric({
                                'statusCode': 5,
                                'errorCode': 4
                            });
                            self.endTour();
                            WalkthroughUtility.logger("VALIDATION STOPPED,QUITTED WALKTHROUGH......");
                            console.groupEnd();
                        } else {
                            self.counter = 0;
                        }
                    }
                    break;
                case 1:
                    if(iscrossoriginelement){
                      if(urlcounter++>3){
                        self.checkIfUserInteracted({
                            'statusCode': 5,
                            'errorCode': 3
                        });    
                      }   
                   }
                    else{
                        self.checkIfUserInteracted({
                        'statusCode': 5,
                        'errorCode': 3
                    });
                    }
                    break;
                case 2:

                    self.checkIfUserInteracted({
                        'statusCode': 5,
                        'errorCode': 5
                    });
                    break;
                // case 3:
                //     window.clearInterval(self.postvalidationIntervalID);
                //     self.showStep();
                //     break;
            }
            //-1 = all case passed
            //1 = url failed
            //2 = element check failed 
            //3 =  element reference failed ( not used currently )
        }, 1000)
    }


    validationBeforeRender() {

 
        this.ongoingStepData = this.ongoingWalkthroughData.templates[this.ongoingStepNumber];
        var self = this;
        var stepurl = this.ongoingStepData.meta.layoutroute;
        var cssId = this.ongoingStepData.meta.targetelementID;
        let elementMeta = this.ongoingStepData.meta.elementMeta;
        WalkthroughUtility.logger("Validation CssID: " + cssId, "group");
        WalkthroughUtility.logger( "Validation Step Url: "+stepurl, "group" )
        // start validating targetElement
        this.targetElement = new WalkthroughTargetElementHandler(cssId, elementMeta);
   
        this.counter = 0;
        this.urlcounter = 0;
        var regenaratorUrl = this.getStepUrl(stepurl);
        this.clearValidationInterval();
        this.prevalidationIntervalID = window.setInterval(() => {
            regenaratorUrl = self.getStepUrl(stepurl);
            self.counter++;
            var result = self.WalkthroughValidator.preRenderValidationInterval(regenaratorUrl, self.targetElement,self.isWildCardMatch);
            //-1 -Element & Url  matched ,
            //1 -> url not matched ,
            //2 -> element not found for 1 minute, so ending tour 
            switch (result) {
                case -1: {
                    //self.ongoingStepElement = WalkthroughUtility.getElement(cssId);
                    self.showStep();
                    self.sendMetric({
                        'statusCode': 1
                    });
                    window.clearInterval(self.prevalidationIntervalID);
                    break;
                }
                case 1: {
                    self.urlcounter++;
                    if (self.urlcounter > 30) { //Url not matched for 15 seconds, so ending tour
                        self.stopIntervel(self.prevalidationIntervalID);
                        WalkthroughUtility.logger("Url not matched for 15 seconds, so ending tour", "groupEnd");
                        self.sendMetric({
                            'statusCode': 4,
                            'errorCode': 1
                        });
                        self.endTour();
                    }
                    break;
                }
                case 2: {
                    if (self.counter > 120) { //Element not found for 1 minute, so ending tour
                        WalkthroughUtility.logger("Element not found for 1 minute, so ending tour", "groupEnd");
                        self.sendMetric({
                            'statusCode': 4,
                            'errorCode': 2
                        });
                        self.stopIntervel(self.prevalidationIntervalID);
                        self.endTour();
                    }
                    else if (self.counter > 4) {
                        self.WalkthroughLayoutManager.hideBackdrop();
                    }
                }
            }
        }, 500)
    }

    stopIntervel(intervalID) {
        window.clearInterval(intervalID);
    }

    loadFlow(flowlist, scope) {

        this.datamanager.loadFlow(flowlist, scope);
    }


    triggerFlow(flowID, medium, promotionId, scope) {
        let flowdata = this.datamanager.WalkthroughData[flowID];
        if (!flowdata) {
            this.datamanager.loadAndTriggerFlow([flowID], medium, promotionId, scope);
            return;
        }

        let existingscope = this.datamanager.WalkthroughData[flowID].scope
        if (existingscope != scope && scope != undefined) {
            this.datamanager.loadAndTriggerFlow([flowID], medium, promotionId, scope);
            return;
        }
        this.promotionId = promotionId;
        let url = flowdata.templates[0].meta.layoutroute;
        if (!this.alwaysOpenInNewTab && medium == "selfhelp" && WalkthroughUtility.isUrlPatternMatch(window.location.href, url, this.isWildCardMatch)
            && this.getProductUrlOrigin(flowdata)==window.location.origin) {
            this.WalkthroughValidator.urlPatternCheck = true;
            this.ongoingWalkthroughData = flowdata;
            this.flowID = flowID;
            this.startTour(this.ongoingWalkthroughData);
            return;
        };
        this.handleTriggerInNewTab(flowID, flowdata, promotionId, url, scope);
    };

    parseWalkthroughData() {
        this.ongoingWalkthroughData = JSON.parse(JSON.stringify(this.ongoingWalkthroughData));
        this.ongoingWalkthroughData = this.bundleParser.parseCss(this.ongoingWalkthroughData, this.workspaceconf);
    };

    constructURL(data) {
        return this.bundleParser.parseURL(data || this.ongoingWalkthroughData, this.workspaceconf, this.dynamicPath);
    }

    sendMetric(data) {
        var orgid = this.datamanager.WalkthroughData[this.flowID].orgid;
        
        let metric = {
            'action': "metrics",
            'walkthroughid': this.flowID,
            'promotionid': this.promotionId,
            'orgid': this.getProductType()== "bundle" ? orgid : this.orgid,
            'sessionstarttime': this.sessionStartTime,
            'stepnumber': this.ongoingStepNumber + 1,
            'statuscode': data.statusCode,
            'errorcode': data.errorCode ? data.errorCode : undefined,
            'serviceid': this.serviceid,
            'Scope': this.datamanager.WalkthroughData[this.flowID].scope
        }


        if (this.promotionId != "-1" && this.promotionId != "0") {
            this.micssdktoserver.sendMetric(metric, "post", () => { }, () => { });
        }

        if (this.metricCallback) {
            try {
                metric["totalsteps"]=this.ongoingWalkthroughData.templates.length;
                this.triggerMetricCallback(metric);
            } catch (error) {
                WalkthroughUtility.logger("metric callback execution failed");
            }
        }

    }

    sendVerificationStatus(status) {
        let param = {
            "flowidlist": [this.flowID],
            "action": "updateWalkthroughStatus",
            "serviceid": this.serviceid,
            "orgid": this.orgid,
            "status": "Verified"

        }

        // function onsuccess() {
        let type = "verify";
        if (this.promotionId == 0) {
            type = "preview";
        }

        window.opener ? window.opener.postMessage({ WalkthroughCallback: true, type: type, status: status }, "*") : ""


    }

    constructPath(url, shouldAddBasePath = false) {
        let scope = this.ongoingWalkthroughData.scope;
        if (scope == "Enterprise") {
            var productname = this.ongoingWalkthroughData.templates[this.ongoingStepNumber].productMeta?.url_product_name;
            return this.urlUtil.constructUrlPathUsingWorkspaceConf(this.workspaceconf, url, productname, shouldAddBasePath);
        }
        else {
            return WalkthroughUtility.constructDynamicURL(url, this.dynamicPath);
        }

    }

    getStepUrl(url) {
        return this.ongoingWalkthroughData.scope == "Enterprise" ? url : WalkthroughUtility.constructDynamicURL(url, this.dynamicPath);
    }

    setupSdk(confForSetup) {
        this.alwaysOpenInNewTab = confForSetup.alwaysStartTourInNewTab ? confForSetup.alwaysStartTourInNewTab : this.alwaysOpenInNewTab;
    }

    handleTriggerInNewTab(flowID, flowdata, promotionId, url, scope) {
        url = this.constructURL(flowdata);
        let origin = this.getProductUrlOrigin(flowdata),
            newWindow;
        if (scope == "Enterprise" && origin != window.location.origin) {
            let message = {
                data: {},
                pid: promotionId,
                action: "smarttour",
                scope: scope,
            };
            message.data[flowID] = flowdata;
            newWindow = window.open(WalkthroughUtility.removeRegexpattern(origin + url));
            const listener = (event) => {
                if (newWindow == event.source && event.data.targetname == "walkthroughsdk" && event.data.status == "readyToStartTour") {
                    newWindow.postMessage({
                        targetname: "micsinproduct",
                        action: "startTour",
                        message: message,
                    }, origin);
                    window.removeEventListener("message", listener);
                }
            };
            window.addEventListener("message", listener);
        } else {
            url = window.location.origin + url;
            newWindow = window.open(WalkthroughUtility.removeRegexpattern(url));
            let json = {
                flowID: flowID,
                PID: promotionId,
                scope: scope,
                orgid: this.orgid
            };
            newWindow.sessionStorage.setItem("currentongoingWalkthroughDataGID", JSON.stringify(json));
            newWindow.sessionStorage.setItem("micsworkspaceconf", JSON.stringify(this.workspaceconf));
            newWindow.sessionStorage.setItem(flowID, JSON.stringify(flowdata));
        }
    }

    getProductUrlOrigin(data) {
        if (data.templates[0].productMeta && this.workspaceconf.productConf
            && this.workspaceconf.productConf[data.templates[0].productMeta.url_product_name]
            && this.workspaceconf.productConf[data.templates[0].productMeta.url_product_name].product_domain) {
            return "https://" + this.workspaceconf.productConf[data.templates[0].productMeta.url_product_name].product_domain;
        }
        return window.location.origin;
    }

    checkIfUserInteracted(errorMetric) {
        if (this.WalkthroughLayoutManager.ongoingStepLayout.querySelector(".backdrop_root #element.clickable") &&
            this.WalkthroughLayoutManager.ongoingStepLayout.querySelector(`[id^="layoutContainer"] #footer-container #row-container .row-child #buttonbuilder #buttoncontainer[goto_action="NextStep"]`)
        ) {
            this.navigateToNextStep();
        } else {
            this.sendMetric(errorMetric);
            this.endTour();
            window.clearInterval(this.postvalidationIntervalID);
            this.validateURLInterval = '';
        }
    }
    enableURLWildCardPatternMatch() {
        this.isWildCardMatch=true;
    }
    disableURLWildCardPatternMatch() {
        this.isWildCardMatch=false;
    }
    startTourOnSamePage() {
        this.alwaysStartInCurrentTab=true;
        this.enableURLWildCardPatternMatch()
    }
    resetStartTourOnSamePage() {
        this.alwaysStartInCurrentTab = false;
        this.disableURLWildCardPatternMatch();
    }
    setWalkthroughStatusCallback(callbackFunction) {
        this.metricCallback = callbackFunction;
    }
    triggerMetricCallback(metric){
        var data = {}
        data.walkthroughid=metric.walkthroughid;
        data.statuscode=metric.statuscode;
        data.stepnumber=metric.stepnumber;
        if(data.stepnumber==1 && data.statuscode==1 || (data.statuscode==1 || data.statuscode==2 ) && data.stepnumber < metric.totalsteps){
            data.status="started";
        }
        else if(metric.totalsteps==data.stepnumber&&data.statuscode==2){
            data.status="completed";    
        }
        else if(metric.totalsteps>data.stepnumber&&data.statuscode==3){
            data.status="quitted";    
        }
        else if(data.statuscode==4||data.statuscode==5){
            data.status="error";  
        }
     
        data.status&&this.metricCallback(data);
    }

}
/* $Id$ */

//Check if PageCollection is already declared;

if (!globalThis.PageCollection) {

    class PageCollection {

        // AbsoluteUrl - complete and valid url
        // RelativeUrl - parts excluding the base url

        constructor(serviceUrlOrigin, urlDynamicIdConf, pageList, urlValidateConf) {
            this.urlDynamicIdConf = (urlDynamicIdConf) ? urlDynamicIdConf : [];
            this.serviceUrlOrigin = serviceUrlOrigin || '';
            this.pageListData = pageList ? pageList : [];
            this.urlRegexRef = {
                search: /\?[^#]*/,
                hash: /#[^#\/\?]*$/,
                hashPath: /#.*/,
                dynamicPartSplit: /\{\{.*?\}\}|\*/,
            };
            this.urlValidationConf = urlValidateConf || { includeSearchParams: false, includeHashValue: false };
        }

        addPage(name, link) {
            this.pages.push({ name, link });
        }

        setPageListData(pageList) {
            this.pageListData = pageList;
        }

        constructAbsoluteUrl(relativeUrl, urlOrigin = this.serviceUrlOrigin) {
            if (this.isLinkValid(relativeUrl)) {
                let url = new URL(relativeUrl);
                relativeUrl = relativeUrl.replace(url.origin, '');
                return this.parseCustomUrlObj(urlOrigin + relativeUrl);
            }
            return this.parseCustomUrlObj(urlOrigin + relativeUrl);
        }

        listPages() {
            return JSON.parse(JSON.stringify(this.pages));
        }

        doesUrlPatternMatch(url, urlPattern) {
            let urlObj = this.parseCustomUrlObj(url);
            let urlPatternObj = this.parseCustomUrlObj(urlPattern);
            let includeSearchParams = (this.urlValidationConf.includeSearchParams || false), includeHashValue = (this.urlValidationConf.includeHashValue || false);
            let splittedUrl = this.splitUrlAsSingleArray(urlObj, includeSearchParams, includeHashValue);
            let splittedPattern = this.splitUrlAsSingleArray(urlPatternObj, includeSearchParams, includeHashValue);

            if (splittedUrl.length === splittedPattern.length
                && ((urlObj.hashPath && urlPatternObj.hashPath && urlObj.hashPathArr.length == urlPatternObj.hashPathArr.length) || (!urlObj.hashPath && !urlPatternObj.hashPath))
                && ((urlObj.search && urlPatternObj.search) || (!urlObj.search && !urlPatternObj.search))
                && ((urlObj.hash && urlPatternObj.hash) || (!urlObj.hash && !urlPatternObj.hash))) {
                for (let i = 0; i < splittedUrl.length; i++) {
                    if (splittedPattern[i] !== splittedUrl[i] && !(this.isDynamicSegment(splittedPattern[i]) && splittedUrl[i] != '')) {
                        return false;
                    }
                }
                return true;
            }

            return false;
        }

        doesUrlWildcardPatternMatch(url, urlPattern) {
            let urlObj = this.parseCustomUrlObj(url);
            let urlPatternObj = this.parseCustomUrlObj(urlPattern);
            let includeSearchParams = (this.urlValidationConf.includeSearchParams || false), includeHashValue = (this.urlValidationConf.includeHashValue || false);

            let newUrl = urlObj.actualPath + (urlObj.hashPath || '')
                + ((urlObj.search && includeSearchParams) ? urlObj.search : '') + ((urlObj.hash && includeHashValue) ? urlObj.hash : '');
            let newUrlPattern = urlPatternObj.actualPath + (urlPatternObj.hashPath || '')
                + ((urlPatternObj.search && includeSearchParams) ? urlPatternObj.search : '') + ((urlPatternObj.hash && includeHashValue) ? urlPatternObj.hash : '');

            if (newUrlPattern === "*") return true;
            let parts = newUrlPattern.split(this.urlRegexRef.dynamicPartSplit).filter(Boolean);
            let currentIndex = 0;
            let isFirst = true;

            for (let part of parts) {
                let pos = newUrl.indexOf(part, currentIndex);
                if (pos === -1) return false;
                if (isFirst && !(newUrlPattern.startsWith("*") || /^{{.*?}}/.test(newUrlPattern)) && pos !== 0) {
                    return false;
                }
                currentIndex = pos + part.length;
                isFirst = false;
            }

            if (!(newUrlPattern.endsWith("*") || /{{.*?}}$/.test(newUrlPattern)) && !newUrl.endsWith(parts[parts.length - 1])) {
                return false;
            }
            return true;
        }
        doesUrlEndsWith_WildcardPatternMatch(url, urlPattern){
            return this.doesUrlWildcardPatternMatch(url, "*"+urlPattern);
        }
        doesUrlEndsWithPattern(url, urlPattern) {
            let urlObj = this.parseCustomUrlObj(url);
            let urlPatternObj = this.parseCustomUrlObj(urlPattern);

            let includeSearchParams = (this.urlValidationConf.includeSearchParams || false), includeHashValue = (this.urlValidationConf.includeHashValue || false);

            let urlArrWithDelimiter = this.splitUrlArrWithDelimiter(urlObj, includeSearchParams, includeHashValue);
            let urlPatternArrWithDelimiter = this.splitUrlArrWithDelimiter(urlPatternObj, includeSearchParams, includeHashValue);

            let lenDiff = urlArrWithDelimiter.length - urlPatternArrWithDelimiter.length;

            if (lenDiff >= 0 || urlPatternArrWithDelimiter.length == 0) {
                urlArrWithDelimiter = urlArrWithDelimiter.slice(lenDiff);
                for (let i = urlPatternArrWithDelimiter.length - 1; i >= 0; i--) {
                    if (urlPatternArrWithDelimiter[i] !== urlArrWithDelimiter[i] && !(this.isDynamicSegment(urlPatternArrWithDelimiter[i]) && urlArrWithDelimiter[i] != '')) {
                        return false;
                    }
                }
                return true;
            }
            return false;
        }

        isDynamicSegment(segment) {
            return /^(\{\{.*?\}\}|\*)$/.test(segment);
        }

        doesPageNameExist(pageName) {
            return this.pageListData.some((page) => {
                return page.name.toLowerCase() === pageName.toLowerCase();
            });
        }

        isLinkConfigurationExist(pagePath) {
            return this.pageListData.some((page) => {
                return this.doesUrlPatternMatch(pagePath, page.link);
            });
        }

        parseCustomUrlObj(link) {
            if (this.isLinkValid(link)) {
                let url = new URL(link);
                link = link.replace(url.origin, '');
            }
            let constructedObj = {};
            constructedObj.origin = this.serviceUrlOrigin ? this.serviceUrlOrigin : '';
            constructedObj.href = constructedObj.origin + link;
            constructedObj.fullPath = link;
            constructedObj.actualPath = constructedObj.fullPath;
            if (constructedObj.fullPath.match(this.urlRegexRef.search) != null) {
                constructedObj.search = constructedObj.fullPath.match(this.urlRegexRef.search)[0];
                constructedObj.searchArr = constructedObj.search.slice(1).split("&");
                constructedObj.actualPath = constructedObj.actualPath.replace(constructedObj.search, '');
            }
            if (constructedObj.fullPath.match(this.urlRegexRef.hash) != null) {
                constructedObj.hash = constructedObj.fullPath.match(this.urlRegexRef.hash)[0];
                constructedObj.hashVal = constructedObj.hash.slice(1);
                constructedObj.actualPath = constructedObj.actualPath.replace(this.urlRegexRef.hash, '');
            }
            if (constructedObj.actualPath.match(this.urlRegexRef.hashPath) != null) {
                constructedObj.hashPath = constructedObj.actualPath.match(this.urlRegexRef.hashPath)[0];
                constructedObj.hashPathArr = constructedObj.hashPath.slice(1).split('/');
                constructedObj.actualPath = constructedObj.actualPath.replace(constructedObj.hashPath, '');
            }
            constructedObj.pathArr = constructedObj.actualPath.split('/');
            return constructedObj;
        }

        replaceUrlDynamicId(urlObj, urlDynamicIdConf) {
            urlDynamicIdConf = urlDynamicIdConf || this.urlDynamicIdConf;
            let validArrJson = {
                pathArr: urlObj.pathArr.filter(x => x != ''),
                hashPathArr: urlObj.hashPath ? urlObj.hashPathArr.filter(x => x != '') : [],
            },
                newUrlObj = JSON.parse(JSON.stringify(urlObj));
            if (urlDynamicIdConf && urlDynamicIdConf.length > 0) {
                urlDynamicIdConf.forEach((conf) => {
                    if (conf.position - 1 < validArrJson.pathArr.length) {
                        newUrlObj = this.markWildcardInUrl(newUrlObj, 'path', conf.position - 1, `{{${conf.dynamicId}}}`);
                    } else if (conf.position - 1 < validArrJson.hashPathArr.length) {
                        newUrlObj = this.markWildcardInUrl(newUrlObj, 'hashPath', conf.position - validArrJson.pathArr.length - 1, `{{${conf.dynamicId}}}`);
                    }
                });
            }
            return newUrlObj;
        }

        markWildcardInUrl(urlObj, urlKey, validIndexPos, markWith = "*") {
            let newUrlObj = JSON.parse(JSON.stringify(urlObj)),
                validIndex = -1;
            switch (urlKey) {
                case "path":
                    for (let i = 0; i < urlObj.pathArr.length; i++) {
                        (newUrlObj.pathArr[i] != "") ? validIndex++ : '';
                        if (validIndex == validIndexPos) {
                            newUrlObj.pathArr[i] = markWith;
                            break;
                        }
                    }
                    newUrlObj.actualPath = newUrlObj.pathArr.join("/");
                    break;
                case "hashPath":
                    for (let i = 0; i < urlObj.hashPathArr.length; i++) {
                        (newUrlObj.hashPathArr[i] != "") ? validIndex++ : '';
                        if (validIndex == validIndexPos) {
                            newUrlObj.hashPathArr[i] = markWith;
                            break;
                        }
                    }
                    newUrlObj.hashPath = '#' + newUrlObj.hashPathArr.join("/");
                    break;
                case "search":
                    for (let i = 0; i < urlObj.searchArr.length; i++) {
                        (newUrlObj.searchArr[i] != "") ? validIndex++ : '';
                        if (validIndex == validIndexPos) {
                            newUrlObj.searchArr[i] = markWith;
                            break;
                        }
                    }
                    newUrlObj.search = "?" + newUrlObj.searchArr.join("&");
                    break;
                case "hash":
                    newUrlObj.hash = "#" + markWith;
                    newUrlObj.hashVal = markWith;
                    break;
            }
            newUrlObj.fullPath = newUrlObj.actualPath + (newUrlObj.hashPath || '') + (newUrlObj.search || '') + (newUrlObj.hash || '');
            newUrlObj.href = newUrlObj.origin + newUrlObj.fullPath;
            return newUrlObj;
        }

        isLinkValid(link) {
            try {
                let url = new URL(link);
                return url;
            } catch (e) {
                return false;
            }
        }

        constructDynamicURL(flowurl, urlDynamicIdConf) {
            if (urlDynamicIdConf && urlDynamicIdConf.length == 0) return flowurl;
            urlDynamicIdConf = urlDynamicIdConf ? urlDynamicIdConf : this.urlDynamicIdConf;
            let url = flowurl;
            let dynamicPatterns = flowurl.match(/\{\{.*?\}\}/g);
            if (dynamicPatterns) {
                dynamicPatterns = dynamicPatterns.map(value => value.slice(2, -2));
                dynamicPatterns.forEach(key => {
                    let dynamicId = urlDynamicIdConf.find(x => x.dynamicId == key);
                    (dynamicId && dynamicId.properties && dynamicId.properties.value) ? url = url.replace(`{{${key}}}`, dynamicId.properties.value) : '';
                });
            }
            return url;
        }

        getContructedBaseUrl(materialConfData) {
            let baseUrl = materialConfData.baseUrl[0].value;
            (materialConfData.urlDynamicIdConf && materialConfData.urlDynamicIdConf.length != 0) ? baseUrl = this.constructDynamicURL(materialConfData.baseUrl[0].value, materialConfData.urlDynamicIdConf) : '';
            return baseUrl;
        }

        getMatchingUrlFromExisting(url, pageList, layoutList, urlDynamicIdConf) {
            pageList = pageList ? pageList : this.pageListData;
            urlDynamicIdConf = urlDynamicIdConf || this.urlDynamicIdConf;
            let urlList = [];

            if (pageList && pageList.length > 0) {
                urlList = urlList.concat(pageList.filter(x => x.type.trim().toLowerCase() === "regex").map(x => x.link));
            }
            if (layoutList && layoutList.length > 0) {
                urlList = urlList.concat(layoutList.map(x => x.layoutroute).filter(x => x.includes("*")));
            }

            let combinedUrl = (urlList.length > 0) ? this.syncWildcardFromList(url, urlList) : url;
            if (combinedUrl === url) {
                let customUrlObj = this.constructAbsoluteUrl(url);
                customUrlObj = this.replaceUrlDynamicId(customUrlObj, urlDynamicIdConf);
                combinedUrl = customUrlObj.fullPath;
            }
            return combinedUrl;
        }

        syncWildcardFromList(url, urlPatternList) {
            urlPatternList = urlPatternList ? urlPatternList : this.pageListData.filter(x => x.type.trim().toLowerCase() === "regex").map(x => x.link);
            let maxMatchedUrl, combinedUrlPattern = url;

            for (let i = 0; i < urlPatternList.length; i++) {
                let urlMatchObj = this.getUrlPatternMatchObj(url, urlPatternList[i]);
                if (urlMatchObj.isFullyMatched) {
                    return urlPatternList[i];
                }
                urlMatchObj.listIndex = i;

                maxMatchedUrl = (urlMatchObj.matchedValidPartsLen > 0 && !maxMatchedUrl)
                    || (maxMatchedUrl && urlMatchObj.matchedValidPartsLen > maxMatchedUrl.matchedValidPartsLen) ? urlMatchObj : maxMatchedUrl;
            }

            if (maxMatchedUrl && maxMatchedUrl.wildcardMatchLen > 0) {
                let urlObj = this.parseCustomUrlObj(this.serviceUrlOrigin + url),
                    urlPatternObj = this.parseCustomUrlObj(this.serviceUrlOrigin + urlPatternList[maxMatchedUrl.listIndex]),
                    splittedPattern = this.splitUrlAsSingleValidArray(urlPatternObj),
                    actualPathMaxPos = urlObj.pathArr.filter(x => x != '').length - 1,
                    hashPathMaxPos = actualPathMaxPos + (urlObj.hashPath ? urlObj.hashPathArr.filter(x => x != '').length - 1 : 0),
                    searchMaxPos = hashPathMaxPos + (urlObj.search ? urlObj.searchArr.filter(x => x != '').length - 1 : 0);

                for (let i = 0; i < maxMatchedUrl.matchedValidPartsLen; i++) {
                    if (this.isDynamicSegment(splittedPattern[i])) {
                        if (i <= actualPathMaxPos) {
                            urlObj = this.markWildcardInUrl(urlObj, "path", i, splittedPattern[i]);
                        } else if (i > actualPathMaxPos && i <= hashPathMaxPos) {
                            urlObj = this.markWildcardInUrl(urlObj, "hashPath", i - actualPathMaxPos - 1, splittedPattern[i]);
                        } else if (i > hashPathMaxPos && i <= searchMaxPos) {
                            urlObj = this.markWildcardInUrl(urlObj, "search", (i - hashPathMaxPos - 1), splittedPattern[i]);
                        } else {
                            urlObj = this.markWildcardInUrl(urlObj, "hash", 0, splittedPattern[i]);
                        }
                    }
                }
                combinedUrlPattern = urlObj.fullPath;
            }

            return combinedUrlPattern;
        }

        splitUrlAsSingleArray(urlObj, includeSearchParams = true, includeHashValue = true) {
            let splittedUrl = urlObj.pathArr;
            splittedUrl = (urlObj.hashPath) ? splittedUrl.concat(urlObj.hashPathArr) : splittedUrl;
            splittedUrl = (urlObj.search && includeSearchParams) ? splittedUrl.concat(urlObj.searchArr) : splittedUrl;
            splittedUrl = (urlObj.hash && includeHashValue) ? splittedUrl.concat([urlObj.hashVal]) : splittedUrl;
            return splittedUrl;
        }

        splitUrlAsSingleValidArray(urlObj) {
            let splittedUrl = urlObj.pathArr.filter(x => x != '');
            splittedUrl = (urlObj.hashPath) ? splittedUrl.concat(urlObj.hashPathArr.filter(x => x != '')) : splittedUrl;
            splittedUrl = (urlObj.search) ? splittedUrl.concat(urlObj.searchArr.filter(x => x != '')) : splittedUrl;
            splittedUrl = (urlObj.hash && urlObj.hashVal) ? splittedUrl.concat([urlObj.hashVal]) : splittedUrl;
            return splittedUrl;
        }

        splitUrlArrWithDelimiter(urlObj, includeSearchParams = false, includeHashValue = false) {
            let splittedUrl = urlObj.actualPath.split(/(\/)/).slice(1);
            splittedUrl = (urlObj.hashPath) ? splittedUrl.concat(urlObj.hashPath.split(/(\#|\/)/).slice(1)) : splittedUrl;
            splittedUrl = (urlObj.search && includeSearchParams) ? splittedUrl.concat(urlObj.search.split(/(\?|\&)/)) : splittedUrl;
            splittedUrl = (urlObj.hash && includeHashValue) ? splittedUrl.concat(["#", urlObj.hashVal]) : splittedUrl;
            return splittedUrl;
        }

        getUrlPatternMatchObj(url, urlPattern) {
            let urlMatchJSON = { matchedLen: 0, matchedValidPartsLen: 0, isFullyMatched: false, dynamicMatchLen: 0, wildcardMatchLen: 0 };
            let urlObj = this.parseCustomUrlObj(this.serviceUrlOrigin + url);
            let urlPatternObj = this.parseCustomUrlObj(this.serviceUrlOrigin + urlPattern);

            for (let i = 0; i < urlObj.pathArr.length; i++) {
                if (i < urlPatternObj.pathArr.length && (urlPatternObj.pathArr[i] === urlObj.pathArr[i] || this.isDynamicSegment(urlObj.pathArr[i]) || (this.isDynamicSegment(urlPatternObj.pathArr[i]) && urlObj.pathArr[i] != ""))) {
                    urlMatchJSON = this.updateUrlMatchJSON(urlMatchJSON, urlObj.pathArr[i], urlPatternObj.pathArr[i]);
                    continue;
                }
                return urlMatchJSON;
            }
            if (urlObj.hashPath) {
                if (!urlPatternObj.hashPath) return urlMatchJSON;
                for (let i = 0; i < urlObj.hashPathArr.length; i++) {
                    if (i < urlPatternObj.hashPathArr.length && (urlPatternObj.hashPathArr[i] === urlObj.hashPathArr[i] || this.isDynamicSegment(urlObj.hashPathArr[i]) || (this.isDynamicSegment(urlPatternObj.hashPathArr[i]) && urlObj.hashPathArr[i] != ""))) {
                        urlMatchJSON = this.updateUrlMatchJSON(urlMatchJSON, urlObj.hashPathArr[i], urlPatternObj.hashPathArr[i]);
                        continue;
                    }
                    return urlMatchJSON;
                }
            }
            if (urlObj.searchArr) {
                if (!urlPatternObj.searchArr) return urlMatchJSON;
                for (let i = 0; i < urlObj.searchArr.length; i++) {
                    if (i < urlPatternObj.searchArr.length && (urlPatternObj.searchArr[i] === urlObj.searchArr[i] || this.isDynamicSegment(urlObj.searchArr[i]) || (this.isDynamicSegment(urlPatternObj.searchArr[i]) && urlObj.searchArr[i] != ""))) {
                        urlMatchJSON = this.updateUrlMatchJSON(urlMatchJSON, urlObj.searchArr[i], urlPatternObj.searchArr[i]);
                        continue;
                    }
                    return urlMatchJSON;
                }
            }
            if (urlObj.hash && urlPatternObj.hash
                && (urlObj.hashVal === urlPatternObj.hashVal || (this.isDynamicSegment(urlPatternObj.hashVal) && urlObj.hashVal != ""))) {
                urlMatchJSON = this.updateUrlMatchJSON(urlMatchJSON, urlObj.hashVal, urlPatternObj.hashVal);
            }
            urlMatchJSON.isFullyMatched = urlMatchJSON.matchedLen == this.splitUrlAsSingleArray(urlObj, true, true).length && urlMatchJSON.matchedLen == this.splitUrlAsSingleArray(urlPatternObj, true, true).length ? true : false;
            return urlMatchJSON;
        }

        updateUrlMatchJSON(urlMatchJSON, urlPart, patternPart) {
            urlMatchJSON.matchedLen++;
            urlPart != '' ? urlMatchJSON.matchedValidPartsLen++ : '';
            this.isDynamicSegment(patternPart) ? urlMatchJSON.dynamicMatchLen++ : '';
            /^(\*)$/.test(patternPart) ? urlMatchJSON.wildcardMatchLen++ : '';
            return urlMatchJSON;
        }

        generateUrlDiffJSON(url, urlPattern) {
            let tempUrl = url;
            let splittedWildcardPattern = urlPattern.split(/(\*)/);
            let updatedUrlSplit = [], tempArr = [], canApply = false;

            for (let i = 0; i < splittedWildcardPattern.length; i++) {
                if (tempUrl.startsWith(splittedWildcardPattern[i])) {
                    tempArr.push({ url: splittedWildcardPattern[i], type: "static" });
                    tempUrl = tempUrl.replace(splittedWildcardPattern[i], "");
                    continue;
                } else if (splittedWildcardPattern[i] == "*" && tempUrl != '') {
                    let str = tempUrl.split(/&|\?|\/|#/)[0];
                    if (str != '' && str != '*') {
                        tempArr.push({ url: str, type: "diff" });
                        canApply = true;
                        tempUrl = tempUrl.replace(str, "");
                        continue;
                    }
                }
                tempArr.push({ url: tempUrl, type: "static" });
                canApply = tempArr.length > 1 ? true : false;
                break;
            }
            updatedUrlSplit = tempArr;

            return {
                json: updatedUrlSplit,
                canApply: canApply,
            };
        }

        setUrlValidationConf(conf) {
            for (let key in conf) {
                this.urlValidationConf[key] = conf[key];
            }
        }

        // Old handling of url

        combineUrlsOnMatch(currrentUrl, pageList) {
            let list = [];
            for (let i = 0; i < pageList.length; i++) {
                let tempurl = pageList[i].link;
                let isUrlMatched = this.URLCheck(currrentUrl, tempurl);
                if (isUrlMatched.matchedlen != 0 || isUrlMatched.isSuccess) {
                    list.push({
                        value: this.mergeUrl(currrentUrl, tempurl, isUrlMatched).url,
                        matchedlen: isUrlMatched.matchedlen,
                        index: i
                    })
                }
            }
            let matchedURL = {
                length: 0,
                index: -1
            };
            for (let i = 0; i < list.length; i++) {
                if (list[i].matchedlen > matchedURL.length) {

                    matchedURL.length = list[i].matchedlen
                    matchedURL.index = i;
                }
            }
            if (matchedURL.length > 0) {
                return list[matchedURL.index].value;
            }
            else {
                return currrentUrl;
            }
        }

        mergeUrl(url1, url2, isUrlMatched) {
            let mergedurl;

            if (isUrlMatched.matchedlen != 0 && url2.search('{{') != -1) {
                if (isUrlMatched.isSuccess) {
                    mergedurl = url2;
                }
                else {
                    mergedurl = url2.substring(0, isUrlMatched.matchedlen) + isUrlMatched.notmatchedUrl;
                }
            }

            return { url: mergedurl, json: isUrlMatched.json };
        }

        URLCheck(url, url_w_pattern) {
            let json = []
            let ogurl = url;
            let og_urlpattern = url_w_pattern;
            if (url_w_pattern == "" || !this.validateDynamicURLSyntax(url_w_pattern)) {
                return { isSuccess: false, reason: "Syntax is wrong!!" };
            }

            let startIndex = 0, endIndex = -1, counter = 0, diffs = [];
            while (counter < 100) {

                startIndex = 0;
                endIndex = url_w_pattern.search("{{");
                let str = "";

                if (endIndex > -1) {
                    str = url_w_pattern.substring(startIndex, endIndex);
                } else if (url_w_pattern == "" || url.endsWith(url_w_pattern)) {
                    let startIndex = url.indexOf(url_w_pattern);
                    if (url_w_pattern == "") {
                        json.push({ url: url.substring(0, url.length), type: "diff" });
                    }
                    else {
                        json.push({ url: url.substring(0, startIndex), type: "diff" });
                        json.push({ url: url.substring(startIndex, url.length), type: "static" });
                    }

                    return { isSuccess: true, reason: "URL is Matching!!", json: json };
                } else {
                    let starts = og_urlpattern.indexOf(url_w_pattern);
                    let start = ogurl.indexOf(url);
                    // let str1 = ogurl.substring(starts,ogurl.length);
                    let matchedlen = url.search('/');

                    let nomatched = ogurl.substring(start + matchedlen, ogurl.length);
                    json.push({ url: url.substring(0, url.search('/')), type: "diff" });
                    json.push({ url: nomatched, type: "static" });
                    return { isSuccess: false, reason: "URL is Mismatching!!", matchedlen: starts, notmatchedUrl: nomatched, json: json };
                }
                if (str == "") {
                    return { isSuccess: true, reason: "URL is Matching!!", json: json };
                } else if (!url.includes(str)) {

                    return { isSuccess: false, reason: "URL Mismatching!!", json: json };
                } else {
                    // console.log('url :> ',url,str,url.search(str),str.length);
                    let start = url.search(str) + str.length;
                    let end = url.length;
                    if (url.search(str) != 0) {
                        json.push({ url: url.substring(0, url.search(str)), type: "diff" });
                        json.push({ url: url.substring(url.search(str), start), type: "static" });
                    }
                    else {
                        json.push({ url: url.substring(0, start), type: "static" });
                    }

                    url = url.substring(start, end);
                    startIndex = url_w_pattern.search("}}") + 2;
                    url_w_pattern = url_w_pattern.substring(startIndex, url_w_pattern.length);
                    //   console.log("URL check: sliced url" + url);
                }
                counter++;
            }

        }

        validateDynamicURLSyntax(url) {
            let istrue = true, counter = 0;
            while (counter < 100) {
                let leftBraceIndx = url.search("{{");
                let rightBraceIndx = url.search("}}");
                //console.log("SYNTAX check: sliced url" + url);
                if (leftBraceIndx > -1 && rightBraceIndx > -1 && this.validateVariableName(url.substring(leftBraceIndx + 2, rightBraceIndx))) {
                    url = url.slice(rightBraceIndx + 2, url.length);
                    //console.log("SYNTAX check: sliced url" + url);
                } else if (leftBraceIndx == -1 && rightBraceIndx == -1) {
                    return true;
                } else {
                    return false;
                }
                counter++;
            }
        }

        validateVariableName(name) {
            return name.match("^[^a-zA-Z_$]|[^\\w$]") == null;
        }

        // new changes

        getUrlType(url) {
            return (url.includes("{{"))
                ? ((url.includes("*")) ? "regex" : "dynamic")
                : ((url.includes("*")) ? "regex" : "static");
        }

        constructUrlPathUsingWorkspaceConf(workspaceConf, productPath, url_product_name,shouldAddBasePath =true ,canConstructDynamicUrl = true) {
            let basepath = '';
            if( url_product_name ){
                (url_product_name == "parent")? url_product_name = workspaceConf.product_name : '';
            } else {
                url_product_name = workspaceConf.activeWorkspace.product_name;
            }
            if (shouldAddBasePath) {
                basepath = workspaceConf.productConf[url_product_name].basepath || '';
                canConstructDynamicUrl && workspaceConf.product_type == "bundle" && basepath.includes('{{') && workspaceConf.walkthroughConf[workspaceConf.product_name].urlDynamicIdConf
                    ? basepath = this.constructDynamicURL(basepath, JSON.parse(workspaceConf.walkthroughConf[workspaceConf.product_name].urlDynamicIdConf)) : '';
            }
            !productPath
                ? productPath = JSON.parse(workspaceConf.walkthroughConf[url_product_name].org_url)[0].value : '';
            canConstructDynamicUrl && productPath.includes('{{') && workspaceConf.walkthroughConf[url_product_name].urlDynamicIdConf
                ? productPath = this.constructDynamicURL(productPath, JSON.parse(workspaceConf.walkthroughConf[url_product_name].urlDynamicIdConf)) : '';
            return basepath + productPath;
        }

        getProductUrlMetaForUrlPath(urlPath, workspaceConf) {
            let product_name = workspaceConf.product_name,
                producturl_regex = workspaceConf.productConf[product_name].producturl_regex;
            if( workspaceConf.product_type == "bundle" ){
                if (product_name!=workspaceConf.activeWorkspace.product_name && new RegExp(workspaceConf.productConf[workspaceConf.activeWorkspace.product_name].producturl_regex).test(urlPath) ){
                    product_name=workspaceConf.activeWorkspace.product_name;
                    producturl_regex = workspaceConf.productConf[product_name].producturl_regex;
                } else {
                    for (let product in workspaceConf.productConf) {
                        if (product!=workspaceConf.product_name && product!=workspaceConf.activeWorkspace.product_name 
                            && new RegExp(workspaceConf.productConf[product].producturl_regex).test(urlPath)) {
                            product_name = product;
                            producturl_regex = workspaceConf.productConf[product].producturl_regex;
                        }
                    }
                }
                product_name == workspaceConf.product_name ? product_name = "parent" : "";
            }
            producturl_regex && (new RegExp(producturl_regex).test(urlPath)) ? urlPath = urlPath.match(new RegExp(producturl_regex))[0] : '';
            return { "product_url_path": urlPath ,"url_product_name": product_name };
        }

        getWorkspaceDomain(workspaceConf){
            if (!workspaceConf) {
                return '';
            }
            
            if (workspaceConf.activeWorkspace && workspaceConf.activeWorkspace.product_name) {
                let activeProductName = workspaceConf.activeWorkspace.product_name;
                if (workspaceConf.productConf && workspaceConf.productConf[activeProductName] 
                    && workspaceConf.productConf[activeProductName].product_domain) {
                    return workspaceConf.productConf[activeProductName].product_domain;
                }
            }
            
            return workspaceConf.product_domain || '';
        }
    }

    globalThis.PageCollection = PageCollection;
}
else {
    //PageCollection Class is already defined
}
/* $Id$ */
const CHAR_LIMIT = 2000;
class RequestContentWrapper extends selfhelpsdk {
    constructor(inproduct, orgID) {
        super(inproduct, orgID);
        this.helphubRequests = [];
        this.unviewedRequestCount = 0;
        this.requestPanelVisible = false;
        this.userNameCache = {};
        this.notificationsData = [];
        this.unreadCount = 0;
        this.USE_DUMMY_DATA = false;
        this.helphubRequestAPI = null;
        RequestContentWrapper.instance = this;
    }

    initialize() {
        var handle = this;
        handle.micssdktoserverInstance = Micssdktoserver.getinstance(
            this.inproductconf,
            this.orgid,
            "selfhelp"
        );
        handle.getdatacallback(handle, "Enterprise");
        if (handle.scope === !"Enterprise") {
            handle.getdatacallback(handle, "Service");
        }
        handle.walkthroughInstance = WalkthroughSDK.getInstance();
        handle.instance = true;

        const bodyelem = document.body;
        bodyelem.insertAdjacentHTML(
            `beforeend`,
            `
    ${this.customplaceholder ? `` : `
      <div id="selfhelpicon" class="${this.styleforDefaultplaceholder.position}">
        <div id="micsselfhelptoggler" style="background-color:${this.styleforDefaultplaceholder.backgroundcolor}">
          <svg width="20px" height="20px" id="helphublogoinwidget" viewBox="0 0 281 246" fill="${this.styleforDefaultplaceholder.fontColor}">
            <path fill-rule="evenodd" clip-rule="evenodd" d="M0 21C0 9.40201 9.40202 0 21 0H259.538C271.136 0 280.538 9.40202 280.538 21V192.992C280.538 204.59 271.136 213.992 259.538 213.992H21C9.40204 213.992 0 204.59 0 192.992V21ZM134.397 91.334C134.397 101.063 129.14 108.949 122.654 108.949C116.168 108.949 110.91 101.063 110.91 91.334C110.91 81.6053 116.168 73.7188 122.654 73.7188C129.14 73.7188 134.397 81.6053 134.397 91.334ZM170.281 108.949C176.766 108.949 182.024 101.063 182.024 91.334C182.024 81.6053 176.766 73.7188 170.281 73.7188C163.795 73.7188 158.537 81.6053 158.537 91.334C158.537 101.063 163.795 108.949 170.281 108.949Z" fill=""/>
            <path d="M143.012 242.675C141.813 244.305 139.377 244.305 138.178 242.675L113.881 209.636C112.424 207.655 113.838 204.859 116.298 204.859H164.893C167.352 204.859 168.767 207.655 167.31 209.636L143.012 242.675Z" fill=""/>
          </svg>
          ${this.renderindicator()}
          ${this.renderDrag()}
        </div>
      </div>
    `}
    <div id="micsselfhelpContainer" class="${this.styleforDefaultplaceholder.position}" style="background:${this.styleforselfhelppopup.listitem.backgroundcolor}">
      <div id="topbar" style="background-color:${this.styleforselfhelppopup.topband.backgroundcolor};color:${this.styleforselfhelppopup.topband.fontColor}">
        <div id="helphublogotextcontainer">
          <svg width="22px" height="22px" viewBox="0 0 281 246" fill="${this.styleforselfhelppopup.topband.fontColor}">
            <path fill-rule="evenodd" clip-rule="evenodd" d="M0 21C0 9.40201 9.40202 0 21 0H259.538C271.136 0 280.538 9.40202 280.538 21V192.992C280.538 204.59 271.136 213.992 259.538 213.992H21C9.40204 213.992 0 204.59 0 192.992V21ZM134.397 91.334C134.397 101.063 129.14 108.949 122.654 108.949C116.168 108.949 110.91 101.063 110.91 91.334C110.91 81.6053 116.168 73.7188 122.654 73.7188C129.14 73.7188 134.397 81.6053 134.397 91.334ZM170.281 108.949C176.766 108.949 182.024 101.063 182.024 91.334C182.024 81.6053 176.766 73.7188 170.281 73.7188C163.795 73.7188 158.537 81.6053 158.537 91.334C158.537 101.063 163.795 108.949 170.281 108.949Z" fill=""/>
            <path d="M143.012 242.675C141.813 244.305 139.377 244.305 138.178 242.675L113.881 209.636C112.424 207.655 113.838 204.859 116.298 204.859H164.893C167.352 204.859 168.767 207.655 167.31 209.636L143.012 242.675Z" fill=""/>
          </svg>
          ${this.renderpopupheader()}
        </div>
        <svg id="micsselfhelpclosableIcon" viewBox="-3 -3 30 30" width="20" height="20" fill="none" stroke="${this.styleforselfhelppopup.topband.fontColor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M18 6L6 18M6 6l12 12"></path>
        </svg>
      </div>
      ${this.renderTabSwitch()}
      ${this.renderTaskbar()}
      <div id="materiallistsearchbar">
        <svg id="searchicon" fill="none" stroke="${this.styleforselfhelppopup.topband.fontColor}" viewBox="0 0 16 16">
          <path d="m14.48,12.18l-3.61-3.61s-.03-.02-.05-.03c.36-.71.58-1.49.58-2.34,0-2.87-2.33-5.2-5.2-5.2S1,3.33,1,6.2s2.33,5.2,5.2,5.2c.85,0,1.63-.22,2.34-.58.01.02.02.03.03.05l3.61,3.61c.32.32.73.47,1.15.47s.83-.16,1.15-.47c.63-.63.63-1.66,0-2.3ZM2,6.2c0-2.32,1.88-4.2,4.2-4.2s4.2,1.88,4.2,4.2-1.88,4.2-4.2,4.2-4.2-1.88-4.2-4.2Zm11.77,7.57c-.24.24-.64.24-.88,0l-3.49-3.5c.33-.26.62-.55.88-.88l3.5,3.49c.24.24.24.64,0,.88Z"></path>
        </svg>
        <input type="text" id="micsselfhelpsearchinput" autocomplete="off" autocorrect="off" autocapitalize="off" placeholder="${this.selfhelpcontents.searchbarplaceholder}">
      </div>
      <div id="materiallistcontainer"></div>
    </div>
  `
        );

        this.togglediv = document.body.lastElementChild;
        if (!this.togglediv || this.togglediv.id !== "micsselfhelpContainer") {
            var node = document.body.lastElementChild;
            while (node && node.id !== "micsselfhelpContainer") node = node.previousElementSibling;
            this.togglediv = node || this.togglediv;
        }
        var toggler = null, selfhelpiconRoot = null;
        if (!this.customplaceholder && this.togglediv) {
            selfhelpiconRoot = this.togglediv.previousElementSibling;
            if (selfhelpiconRoot && selfhelpiconRoot.id === "selfhelpicon") {
                toggler = selfhelpiconRoot.querySelector("#micsselfhelptoggler");
            }
        }
        if (toggler) toggler.addEventListener("click", this.showselfhelpPopup.bind(this));
        this.applyplaceholderstyles();
        var closeIcon = this.togglediv ? this.togglediv.querySelector("#micsselfhelpclosableIcon") : null;
        if (closeIcon) closeIcon.addEventListener("click", this.showselfhelpPopup.bind(this));
        var searchInput = this.togglediv ? this.togglediv.querySelector("#micsselfhelpsearchinput") : null;
        if (searchInput) searchInput.addEventListener("keyup", function () {
            handle.materialsearch(handle);
        });
        this.urlchangeListner();
        this.tabswitch(this.selectedtab);
        this.selfhelpcontents.floating ? this.enableDrag("selfhelpicon", "micsselfhelpContainer") : "";
        this.initTabListeners();
        this.addListInMaterial();
        var userHelpRequestEnabled = false;
        try {
            if (typeof dapmodulesconfig !== "undefined"
                && dapmodulesconfig
                && dapmodulesconfig.userhelprequest === true) {
                userHelpRequestEnabled = true;
            }
        } catch (e) { }

        if (userHelpRequestEnabled) {
            this.helphubRequestAPI = Micssdktoserver.getinstance(this.inproductconf, this.orgid, "helprequest");
            this.injectRequestContentButton();
            this.initHelpHubRequestFeature();
        }
    }

    initHelpHubRequestFeature() {
        this.loadUserPastRequests();
        this.initRequestPanelUrlListener();
    }

  
    initRequestPanelUrlListener() {
        if (this.requestPanelUrlListenerBound) return;
        this.requestPanelUrlListenerBound = true;
        var handle = this;
        var lastUrl = location.href;

        function onUrlMaybeChanged() {
        
            clearTimeout(handle.urlChangeDebounce);
            handle.urlChangeDebounce = setTimeout(function () {
                if (location.href === lastUrl) return;
                lastUrl = location.href;
                handle.handleProductContextChange();
            }, 180);
        }

        try {
            var originalPushState = history.pushState;
            history.pushState = function () {
                var ret = originalPushState.apply(history, arguments);
                onUrlMaybeChanged();
                return ret;
            };
            var originalReplaceState = history.replaceState;
            history.replaceState = function () {
                var ret = originalReplaceState.apply(history, arguments);
                onUrlMaybeChanged();
                return ret;
            };
        } catch (e) { }

        window.addEventListener("popstate", onUrlMaybeChanged);
        window.addEventListener("hashchange", onUrlMaybeChanged);

        setInterval(function () {
            if (location.href !== lastUrl) {
                lastUrl = location.href;
                handle.handleProductContextChange();
            }
        }, 1000);
    }

   
    handleProductContextChange() {
        var handle = this;

        // Reload past requests in the background so the next open is fresh.
        try { handle.loadUserPastRequests(); } catch (e) { }

     
        try {
            var existingPanel = handle.findInWidget
                ? handle.findInWidget("helphub-request-panel")
                : document.getElementById("helphub-request-panel");
            if (!existingPanel) return;

            var inNewRequestForm = !!existingPanel.querySelector("#helphub-new-request-form");
            var inFollowupView   = !!existingPanel.querySelector("#helphub-followup-view");
            if (inNewRequestForm || inFollowupView) return;

            existingPanel.remove();
            handle.requestPanelVisible = false;

            var container = handle.getWidgetRoot();
            if (container) container.style.overflow = "";
        } catch (e) { }
    }

    getActiveWorkspaceConf() {
        try {
            if (this.walkthroughInstance && this.walkthroughInstance.workspaceconf
                && Object.keys(this.walkthroughInstance.workspaceconf).length > 0) {
                return this.walkthroughInstance.workspaceconf;
            }
        } catch (e) { }
        try {
            var raw = sessionStorage.getItem("micsworkspaceconf")
                || sessionStorage.getItem("workspaceConf");
            if (raw) return JSON.parse(raw);
        } catch (e) { }
        return null;
    }

    getActiveProductMeta() {
        var meta = {
            workspaceConf: null,
            urlMeta: null,
            productName: "",
            productUrlPath: "",
            productScopeId: "",
            isBundle: false,
            isOnboarded: false
        };
        var workspaceConf = this.getActiveWorkspaceConf();
        if (!workspaceConf) return meta;
        meta.workspaceConf = workspaceConf;
        meta.isBundle = (workspaceConf.product_type === "bundle");

        var urlPath = (window.location.pathname || "") + (window.location.search || "");
        var fullUrl = window.location.href || "";
        var hostPath = (window.location.host || "") + urlPath;
        var parentName = workspaceConf.product_name || "";

        function safeTest(regex, str) {
            if (!regex || !str) return false;
            try { return new RegExp(regex).test(str); } catch (e) { return false; }
        }
      
        function regexMatchesAny(regex) {
            return safeTest(regex, urlPath)
                || safeTest(regex, fullUrl)
                || safeTest(regex, hostPath);
        }

        // -------- Non-bundle product --------
        if (!meta.isBundle) {
            meta.productName = parentName;
            meta.productUrlPath = urlPath;
            var parentRegex = workspaceConf.productConf
                && workspaceConf.productConf[parentName]
                && workspaceConf.productConf[parentName].producturl_regex;
            // If no regex configured, assume onboarded (single product workspace).
            meta.isOnboarded = parentRegex ? regexMatchesAny(parentRegex) : true;
            meta.urlMeta = { url_product_name: parentName, product_url_path: urlPath };
            // Non-bundle: no override; the SDK's own orgid is correct.
            meta.productScopeId = "";
            return meta;
        }

        // -------- Bundle product: detect the active sub-product and pick its scope id --------
        if (!workspaceConf.productConf) return meta;

        try {
            if (this.urlUtil && typeof this.urlUtil.getProductUrlMetaForUrlPath === "function") {
                meta.urlMeta = this.urlUtil.getProductUrlMetaForUrlPath(urlPath, workspaceConf);
            }
        } catch (e) { }

        var matchedProduct = "";

        if (meta.urlMeta
            && meta.urlMeta.url_product_name
            && meta.urlMeta.url_product_name !== "parent"
            && workspaceConf.productConf[meta.urlMeta.url_product_name]) {
            matchedProduct = meta.urlMeta.url_product_name;
        }

        if (!matchedProduct) {
            try {
                for (var p in workspaceConf.productConf) {
                    if (p === parentName) continue;
                    var subRegex = workspaceConf.productConf[p]
                        && workspaceConf.productConf[p].producturl_regex;
                    if (regexMatchesAny(subRegex)) { matchedProduct = p; break; }
                }
            } catch (e) { }
        }

        if (!matchedProduct) {
            var parentRx = workspaceConf.productConf[parentName]
                && workspaceConf.productConf[parentName].producturl_regex;
            if (regexMatchesAny(parentRx)) matchedProduct = parentName;
        }

        if (!matchedProduct) {
            meta.isOnboarded = false;
            return meta;
        }

        meta.isOnboarded = true;
        meta.productName = matchedProduct;
        var urlProductName = (matchedProduct === parentName) ? "parent" : matchedProduct;
        meta.urlMeta = {
            url_product_name: urlProductName,
            product_url_path: urlPath
        };
        meta.productUrlPath = urlPath;

        var scopeId = workspaceConf.productConf[matchedProduct]
            && workspaceConf.productConf[matchedProduct].product_scopeid;
        meta.productScopeId = (scopeId !== undefined && scopeId !== null && String(scopeId) !== "")
            ? String(scopeId) : "";
        return meta;
    }

   
   
    isRequestForActiveProduct(req) {
        return !!req;
    }

    applySubProductScope(params) {
        return params;
    }


    fanoutToBroadcastSiblings(requestId, baseParams, onAnyComplete) {
        var handle = this;
        if (!handle.helphubRequestAPI) return;

        var visibleReq = (handle.helphubRequests || []).find(function (r) {
            return String(r.id) === String(requestId);
        });
        var rawSiblings = (visibleReq && Array.isArray(visibleReq.broadcastSiblings))
            ? visibleReq.broadcastSiblings.slice()
            : [{ reqId: String(requestId), scopeId: "" }];

       
        var seen = {};
        var siblings = [];
        rawSiblings.forEach(function (s) {
            var rid = String(s.reqId || "");
            if (!rid || seen[rid]) return;
            seen[rid] = true;
            siblings.push(s);
        });

        if (!siblings.length) {
            siblings = [{ reqId: String(requestId), scopeId: "" }];
        }

        var pending = siblings.length;
        function done() {
            pending--;
            if (pending <= 0 && typeof onAnyComplete === "function") {
                try { onAnyComplete(); } catch (e) { }
            }
        }

       
        var isBundleWorkspace = false;
        var parentOrgIdStr = "";
        try {
            var meta = handle.getActiveProductMeta();
            isBundleWorkspace = !!(meta && meta.isBundle);
            parentOrgIdStr = String(handle.orgid || "");
        } catch (e) { }

        siblings.forEach(function (s) {
            var p = Object.assign({}, baseParams);
            p.reqId = String(s.reqId);
            if (isBundleWorkspace && s.scopeId) {
                var scopeStr = String(s.scopeId);
                p.orgid = scopeStr;
                p.ORGID = scopeStr;
                if (parentOrgIdStr && scopeStr === parentOrgIdStr) {
                    delete p.sub_product_orgid;
                } else {
                    p.sub_product_orgid = scopeStr;
                }
            }
            try {
                handle.helphubRequestAPI.submitRemark(p, function () {
                    done();
                }, function () {
                    done();
                });
            } catch (e) {
                done();
            }
        });
    }

   
    cacheRequestForAllSiblings(requestId, fields) {
        var handle = this;
        var ids = {};
        ids[String(requestId)] = true;
        var visibleReq = (handle.helphubRequests || []).find(function (r) {
            return String(r.id) === String(requestId);
        });
        if (visibleReq && Array.isArray(visibleReq.broadcastSiblings)) {
            visibleReq.broadcastSiblings.forEach(function (s) {
                if (s && s.reqId) ids[String(s.reqId)] = true;
            });
        }
        Object.keys(ids).forEach(function (rid) {
            handle.cacheRequest(rid, fields);
        });
    }

    getWidgetRoot() {
        return this.togglediv || null;
    }
    findInWidget(id) {
        var root = this.getWidgetRoot();
        if (!root || !id) return null;
        try { return root.querySelector("#" + id); } catch (e) { return null; }
    }
    findAllInWidget(selector) {
        var root = this.getWidgetRoot();
        if (!root || !selector) return [];
        try { return root.querySelectorAll(selector); } catch (e) { return []; }
    }

    getRequestCacheKey() {
        return "helphub_req_cache_" + (this.orgid || "default");
    }
    readRequestCache() {
        try {
            var raw = localStorage.getItem(this.getRequestCacheKey());
            return raw ? (JSON.parse(raw) || {}) : {};
        } catch (e) { return {}; }
    }
    writeRequestCache(cache) {
        try {
            localStorage.setItem(this.getRequestCacheKey(), JSON.stringify(cache || {}));
        } catch (e) { }
    }

    getPendingSubmissionsKey() {
        return "helphub_pending_submissions_" + (this.orgid || "default");
    }
    readPendingSubmissions() {
        try {
            var raw = localStorage.getItem(this.getPendingSubmissionsKey());
            var list = raw ? JSON.parse(raw) : [];
            return Array.isArray(list) ? list : [];
        } catch (e) { return []; }
    }
    writePendingSubmissions(list) {
        try {
            localStorage.setItem(
                this.getPendingSubmissionsKey(),
                JSON.stringify(Array.isArray(list) ? list : [])
            );
        } catch (e) { }
    }
    prunePendingSubmissions(list) {
        // Drop entries older than 24h so this list cannot grow unbounded.
        var cutoff = Date.now() - 24 * 60 * 60 * 1000;
        return (list || []).filter(function (p) {
            return p && Number(p.time) >= cutoff;
        });
    }
    addPendingSubmission(description, contentType) {
        if (!description || !contentType) return;
        var list = this.prunePendingSubmissions(this.readPendingSubmissions());
        list.push({
            description: String(description),
            contentType: String(contentType),
            time: Date.now()
        });
        this.writePendingSubmissions(list);
    }
    findPendingContentType(description, rawTime) {
        if (!description) return "";
        var list = this.prunePendingSubmissions(this.readPendingSubmissions());
        var desc = String(description);
        var ts = Number(rawTime) || 0;
        // Prefer the closest-in-time entry with the same description.
        var best = null;
        var bestDelta = Infinity;
        for (var i = 0; i < list.length; i++) {
            var p = list[i];
            if (!p || p.description !== desc || !p.contentType) continue;
            var delta = ts ? Math.abs((Number(p.time) || 0) - ts) : 0;
            if (delta < bestDelta) {
                best = p;
                bestDelta = delta;
            }
        }
        return best ? best.contentType : "";
    }

    cacheRequest(id, fields) {
        if (!id) return;
        var cache = this.readRequestCache();
        var prev = cache[String(id)] || {};
        var merged = Object.assign({}, prev, fields || {});
        if (!merged.followups) merged.followups = prev.followups || [];
        cache[String(id)] = merged;
        this.writeRequestCache(cache);
    }
    cacheFollowup(id, description, rawTime) {
        if (!id || !description) return;
        var cache = this.readRequestCache();
        var entry = cache[String(id)] || {};
        entry.followups = entry.followups || [];
        var ts = Number(rawTime) || Date.now();
        var exists = entry.followups.some(function (f) {
            return String(f.description) === String(description) &&
                Math.abs((Number(f.rawTime) || 0) - ts) < 2000;
        });
        if (!exists) {
            entry.followups.push({ description: String(description), rawTime: ts });
            entry.followups.sort(function (a, b) {
                return (Number(a.rawTime) || 0) - (Number(b.rawTime) || 0);
            });
        }
        cache[String(id)] = entry;
        this.writeRequestCache(cache);
    }

    cacheAction(id, actionEntry) {
        if (!id || !actionEntry || !actionEntry.action) return;
        var cache = this.readRequestCache();
        var entry = cache[String(id)] || {};
        entry.actions = entry.actions || [];
        var ts = Number(actionEntry.rawTime) || 0;
        if (!ts) return;
        var exists = entry.actions.some(function (a) {
            return String(a.action) === String(actionEntry.action) &&
                Math.abs((Number(a.rawTime) || 0) - ts) < 1500 &&
                String(a.rawDescription || "") === String(actionEntry.rawDescription || "");
        });
        if (!exists) {
            entry.actions.push({
                action: String(actionEntry.action).toUpperCase(),
                rawTime: ts,
                rawDescription: String(actionEntry.rawDescription || ""),
                rawMaterialId: String(actionEntry.rawMaterialId || ""),
                materialType: String(actionEntry.materialType || "BANNER").toUpperCase(),
                spaceId: String(actionEntry.spaceId || ""),
                profileUrl: String(actionEntry.profileUrl || "")
            });
            entry.actions.sort(function (a, b) {
                return (Number(a.rawTime) || 0) - (Number(b.rawTime) || 0);
            });
        }
        cache[String(id)] = entry;
        this.writeRequestCache(cache);
    }

    parseAcceptEntryDetails(acceptEntry, fallbackContentTypeLabel, CONTENT_LABEL) {
        var handle = this;
        var responseLink = null;
        var contentName = null;
        var materialId = null;
        var responseContextText = "";
        var contentTypeLabel = fallbackContentTypeLabel;

        if (!acceptEntry) {
            return { responseLink: null, contentName: null, materialId: null,
                responseContextText: "", contentTypeLabel: contentTypeLabel };
        }

        var packed = acceptEntry.rawDescription || "";
        var serverUrl = "";
        var serverName = "";

        if (packed.indexOf("||") !== -1) {
            var parts = packed.split("||");
            if (parts.length === 3) {
                serverUrl = parts[0].trim();
                serverName = parts[1].trim();
                responseContextText = parts[2].trim();
            } else if (parts.length >= 4) {
                serverUrl = parts[0].trim();
                serverName = parts[1].trim();
                var origType = parts[2].trim();
                responseContextText = parts[3].trim();
                if (origType && origType !== "0" && origType !== "-1") {
                    var cleanOrigType = origType.toUpperCase().replace(/ /g, "");
                    if (CONTENT_LABEL[cleanOrigType]) {
                        contentTypeLabel = CONTENT_LABEL[cleanOrigType];
                    } else if (cleanOrigType === "EXTERNALCONTENT") {
                        contentTypeLabel = "External Resource";
                    } else {
                        contentTypeLabel = origType;
                    }
                }
            }
        }

        var resolvedMatId = acceptEntry.rawMaterialId;
        materialId = (resolvedMatId && resolvedMatId !== "-1" && resolvedMatId !== "0")
            ? resolvedMatId : null;
        contentName = (serverName && serverName !== "-1" && serverName !== "")
            ? serverName : null;

        var isAbsoluteUrl = serverUrl && serverUrl.startsWith("http");
        var isRelativePath = serverUrl &&
            (serverUrl.indexOf("/dap/") !== -1 || serverUrl.indexOf("/mics/") !== -1);

        if (isAbsoluteUrl) {
            responseLink = serverUrl;
        } else if (isRelativePath) {
            var origin = window.location.origin;
            try {
                var dc = handle.domainConf;
                if (dc && dc.domain && dc.domainType && dc.domain[dc.domainType]) {
                    origin = window.location.protocol + "//" + dc.domain[dc.domainType];
                }
            } catch (e) { }
            responseLink = origin + (serverUrl.startsWith("/") ? serverUrl : "/" + serverUrl);
        } else if (materialId) {
            var workspaceId = String(acceptEntry.spaceId || "").trim();
            if (!workspaceId || workspaceId === "0") {
                try {
                    var mwc = sessionStorage.getItem("micsworkspaceconf") ||
                        sessionStorage.getItem("workspaceConf");
                    if (mwc) {
                        var pw = JSON.parse(mwc);
                        workspaceId = pw.workspaceID || pw.workspaceid ||
                            pw.orgid || pw.orgId || pw.id || "";
                    }
                } catch (e) { }
            }
            if (!workspaceId || workspaceId === "0") {
                workspaceId = String(
                    window.zsoid || window.ZSOID ||
                    window.orgid || window.orgId ||
                    window.portalId || window.portalID ||
                    window.ZORGID || ""
                );
            }
            var urlSegMap = {
                WALKTHROUGH: "smarttour",
                INTERACTIVEVIDEO: "interactivevideo",
                GUIDE: "guide",
                BANNER: "banner",
                EXTERNALRESOURCE: "externalresource"
            };
            var seg = urlSegMap[acceptEntry.materialType] ||
                acceptEntry.materialType.toLowerCase().replace(/ /g, "");
            var svcName = (handle.domainConf && handle.domainConf.servicename)
                ? handle.domainConf.servicename
                : (handle.serviceid || "CRM");
            var cDomain = window.location.origin;
            try {
                var dcf = handle.domainConf;
                if (dcf && dcf.domain && dcf.domainType && dcf.domain[dcf.domainType]) {
                    cDomain = window.location.protocol + "//" + dcf.domain[dcf.domainType];
                }
            } catch (e) { }
            responseLink = (workspaceId && workspaceId !== "0")
                ? cDomain + "/dap/" + seg + "/" + svcName + "/" + workspaceId + "/" + materialId
                : cDomain + "/mics/" + seg + "/" + svcName + "/" + materialId;
        }

        return {
            responseLink: responseLink,
            contentName: contentName,
            materialId: materialId,
            responseContextText: responseContextText,
            contentTypeLabel: contentTypeLabel
        };
    }

    loadUserPastRequests() {
        var handle = this;
        var requestCache = handle.readRequestCache();
        var baseParams = {
            action: "viewUserPastRequest",
            orgid: this.orgid,
            Scope: this.scope
        };

        var isBundleCase = false;
        var bundleWorkspaceId = "";
        var scopeIds = [];
        try {
            var meta = handle.getActiveProductMeta();
            if (meta && meta.isBundle && meta.workspaceConf) {
                isBundleCase = true;
                try {
                    if (typeof micsUtilStoreFramework !== "undefined" &&
                        micsUtilStoreFramework &&
                        typeof micsUtilStoreFramework.getItem === "function") {
                        var wc = micsUtilStoreFramework.getItem("workspaceConf");
                        if (wc && wc.product_workspaceid !== undefined && wc.product_workspaceid !== null) {
                            bundleWorkspaceId = String(wc.product_workspaceid);
                        }
                    }
                } catch (e) { }
                if (!bundleWorkspaceId && meta.workspaceConf.product_workspaceid) {
                    bundleWorkspaceId = String(meta.workspaceConf.product_workspaceid);
                }
            }
        } catch (e) { }
      
        scopeIds = [String(this.orgid)];

        function buildParams(scopeId) {
            var p = Object.assign({}, baseParams);

            if (isBundleCase) {
              
                if (bundleWorkspaceId) {
                    p.product_workspaceid = bundleWorkspaceId;
                }
                try {
                    if (meta && meta.workspaceConf) {
                        p.product_type = "bundle";
                        p.parent_product_name = meta.workspaceConf.product_name || "";
                        if (meta.productName) {
                            p.product_name = meta.productName;
                            p.url_product_name = meta.urlMeta
                                ? meta.urlMeta.url_product_name
                                : meta.productName;
                        }
                        if (meta.productUrlPath) {
                            p.product_url_path = meta.productUrlPath;
                        }
                    }
                } catch (e) { }
                return p;
            }
            if (scopeId && String(scopeId) !== String(handle.orgid)) {
                p.orgid = scopeId;
                p.ORGID = scopeId;
                p.sub_product_orgid = scopeId;
            }
            return p;
        }

        var pending = scopeIds.length;
        var aggregatedRows = [];

        function onAllDone() {
            var mergedResponse = JSON.stringify(aggregatedRows);
            handleFetchSuccess(mergedResponse);
        }

        scopeIds.forEach(function (sid) {
            var fetchParams = buildParams(sid);
           
            handle.helphubRequestAPI.fetchHelpRequests(
                fetchParams,
                function (response) {
                   
                    try {
                        var data = response ? JSON.parse(response) : [];
                        var list = Array.isArray(data)
                            ? data
                            : (data && typeof data === "object" ? Object.values(data) : []);
                        var actionsSeen = list.map(function (r) {
                            return {
                                req: r && (r.REQUEST_ID || r.reqId),
                                action: r && r.ACTION,
                                space: r && r.SPACE_ID
                            };
                        });
                      
                        list.forEach(function (row) {
                            if (row && typeof row === "object") {
                                row.__fetchedScopeId = String(sid);
                            }
                            aggregatedRows.push(row);
                        });
                    } catch (e) { }
                    pending--;
                    if (pending <= 0) onAllDone();
                },
                function () {
                    pending--;
                    if (pending <= 0) onAllDone();
                }
            );
        });

        function handleFetchSuccess(response) {
                try {
                    var data = response ? JSON.parse(response) : [];
                    var rawList = Array.isArray(data)
                        ? data
                        : (data && typeof data === "object" ? Object.values(data) : []);

                    var lastViewed = Number(localStorage.getItem("helphub_last_viewed") || 0);
                    var unviewedCount = 0;

                    function readField(row, key) {
                        if (row[key] !== undefined && row[key] !== null) {
                            var v = row[key];
                            return (v && typeof v === "object" && v.displayname !== undefined)
                                ? String(v.displayname)
                                : String(v);
                        }
                        var normalized = key.toUpperCase().replace(/_/g, "");
                        var keys = Object.keys(row);
                        for (var i = 0; i < keys.length; i++) {
                            if (keys[i].toUpperCase().replace(/_/g, "") === normalized) {
                                var v2 = row[keys[i]];
                                if (v2 === null || v2 === undefined) return "";
                                return (v2 && typeof v2 === "object" && v2.displayname !== undefined)
                                    ? String(v2.displayname)
                                    : String(v2);
                            }
                        }
                        return "";
                    }

                    var ACTION_MAP = {
                        "0": "RAISED", "1": "ACCEPT", "2": "DECLINE",
                        "3": "REOPEN", "4": "COMPLETED"
                    };
                    var MATERIAL_MAP = {
                        "0": "BANNER", "1": "INTERACTIVEVIDEO",
                        "2": "GUIDE", "3": "WALKTHROUGH",
                        "4": "EXTERNALRESOURCE"
                    };
                    var CONTENT_LABEL = {
                        WALKTHROUGH: "Walkthrough",
                        INTERACTIVEVIDEO: "Interactive Video",
                        GUIDE: "Guide",
                        BANNER: "Banner",
                        EXTERNALRESOURCE: "External Resource"
                    };

                    var allEntries = rawList
                        .filter(function (r) { return r && typeof r === "object"; })
                        .map(function (r) {
                            var actionRaw = readField(r, "ACTION");
                            var action = (ACTION_MAP[actionRaw] || actionRaw || "RAISED").toUpperCase();
                            var mtRaw = readField(r, "MATERIAL_TYPE");
                            var materialType = (MATERIAL_MAP[mtRaw] || mtRaw || "GUIDE").toUpperCase();
                            var requestId = readField(r, "REQUEST_ID") ||
                                readField(r, "reqId") ||
                                readField(r, "REQID");
                            if (!requestId || requestId === "0") return null;

                            return {
                                requestId: requestId,
                                action: action,
                                materialType: materialType,
                                contentLabel: CONTENT_LABEL[materialType] || materialType || "Guide",
                                rawDescription: String(readField(r, "DESCRIPTION") || "").trim(),
                                rawMaterialId: String(readField(r, "MATERIAL_ID") || "").trim(),
                                rawTime: Number(readField(r, "TIME")) || 0,
                                spaceId: readField(r, "SPACE_ID") ||
                                    readField(r, "WORKSPACE_ID") ||
                                    readField(r, "orgId") ||
                                    readField(r, "orgid") || "",
                                profileUrl: readField(r, "PROFILE") || "",
                                productName: readField(r, "PRODUCT_NAME") ||
                                    readField(r, "product_name") || "",
                                urlProductName: readField(r, "URL_PRODUCT_NAME") ||
                                    readField(r, "url_product_name") || "",
                                pageUrl: readField(r, "URL_CHAR") ||
                                    readField(r, "PAGE_URL") ||
                                    readField(r, "pageUrl") || "",
                                fetchedScopeId: String(r.__fetchedScopeId || "")
                            };
                        })
                        .filter(function (e) { return e && e.requestId; });

                    allEntries.forEach(function (e) {
                        handle.cacheAction(e.requestId, {
                            action: e.action,
                            rawTime: e.rawTime,
                            rawDescription: e.rawDescription,
                            rawMaterialId: e.rawMaterialId,
                            materialType: e.materialType,
                            spaceId: e.spaceId,
                            profileUrl: e.profileUrl
                        });
                    });

                    requestCache = handle.readRequestCache();

                    var serverKeyByRid = {};
                    var serverHasAcceptByRid = {};
                    allEntries.forEach(function (e) {
                        var rid = String(e.requestId);
                        serverKeyByRid[rid] = serverKeyByRid[rid] || {};
                        serverKeyByRid[rid][e.action + "_" + e.rawTime] = true;
                        if (e.action === "ACCEPT" || e.action === "COMPLETED") {
                            serverHasAcceptByRid[rid] = true;
                        }
                    });

                    Object.keys(requestCache).forEach(function (rid) {
                        var cached = requestCache[rid] || {};
                        var cachedActions = Array.isArray(cached.actions) ? cached.actions : [];
                        cachedActions.forEach(function (a) {
                            if (!a || !a.action || !a.rawTime) return;
                            var actUpper = String(a.action).toUpperCase();
                            if (serverHasAcceptByRid[rid] &&
                                (actUpper === "ACCEPT" || actUpper === "COMPLETED")) {
                                return;
                            }
                            var seenKey = (actUpper + "_" + a.rawTime);
                            if (serverKeyByRid[rid] && serverKeyByRid[rid][seenKey]) return;
                            allEntries.push({
                                requestId: rid,
                                action: actUpper,
                                materialType: String(a.materialType || "BANNER").toUpperCase(),
                                contentLabel: CONTENT_LABEL[String(a.materialType || "BANNER").toUpperCase()] || "Guide",
                                rawDescription: String(a.rawDescription || ""),
                                rawMaterialId: String(a.rawMaterialId || ""),
                                rawTime: Number(a.rawTime) || 0,
                                spaceId: String(a.spaceId || ""),
                                profileUrl: String(a.profileUrl || "")
                            });
                            serverKeyByRid[rid] = serverKeyByRid[rid] || {};
                            serverKeyByRid[rid][seenKey] = true;
                        });
                    });

                    var grouped = {};
                    allEntries.forEach(function (e) {
                        var rid = String(e.requestId);
                        if (!grouped[rid]) grouped[rid] = [];
                        grouped[rid].push(e);
                    });

                    var finalRequests = [];

                    Object.keys(grouped).forEach(function (rid) {
                        var entries = grouped[rid];
                        entries.sort(function (a, b) { return a.rawTime - b.rawTime; });

                        var raisedEntry = entries.find(function (e) { return e.action === "RAISED"; });

                        var acceptEntries = entries.filter(function (e) {
                            return e.action === "ACCEPT" || e.action === "COMPLETED";
                        });
                        var acceptEntry = acceptEntries.length > 0
                            ? acceptEntries[acceptEntries.length - 1]
                            : null;

                        var declineEntries = entries.filter(function (e) { return e.action === "DECLINE"; });
                        var declineEntry = declineEntries.length > 0
                            ? declineEntries[declineEntries.length - 1]
                            : null;

                        var reopenEntries = entries.filter(function (e) { return e.action === "REOPEN"; })
                            .map(function (re) {
                                return Object.assign({}, re, {
                                    date: handle.formatRequestTime(re.rawTime)
                                });
                            });

                        var latestEntry = entries[entries.length - 1];
                        var latestAction = latestEntry.action;

                        var derivedStatus;
                        if (latestAction === "ACCEPT" || latestAction === "COMPLETED") {
                            derivedStatus = "completed";
                        } else if (latestAction === "DECLINE") {
                            derivedStatus = "declined";
                        } else if (latestAction === "REOPEN") {
                            derivedStatus = "remarked";
                        } else {
                            derivedStatus = "open";
                        }

                        var isRead = (latestAction === "RAISED" || latestAction === "REOPEN");
                        if (!isRead && latestEntry.rawTime > lastViewed) unviewedCount++;

                        var originalDescription = "";
                        var firstReopenTime = Number.MAX_SAFE_INTEGER;
                        for (var _ri = 0; _ri < entries.length; _ri++) {
                            if (entries[_ri].action === "REOPEN" && entries[_ri].rawTime < firstReopenTime) {
                                firstReopenTime = entries[_ri].rawTime;
                            }
                        }
                        var raisedBeforeReopen = entries.filter(function (e) {
                            return e.action === "RAISED" && e.rawTime < firstReopenTime;
                        });
                        var effectiveRaisedEntry = raisedBeforeReopen.length > 0
                            ? raisedBeforeReopen[raisedBeforeReopen.length - 1]
                            : raisedEntry;
                        if (effectiveRaisedEntry) {
                            var raw = effectiveRaisedEntry.rawDescription;
                            if (raw && raw !== "-1" && raw !== "0") {
                                originalDescription = raw;
                            }
                        }


                        if (!originalDescription) {
                            var reopenEntriesAsc = entries
                                .filter(function (e) { return e.action === "REOPEN"; })
                                .sort(function (a, b) { return a.rawTime - b.rawTime; });
                            for (var _re = 0; _re < reopenEntriesAsc.length; _re++) {
                                var rd = reopenEntriesAsc[_re].rawDescription;
                                if (rd && rd !== "-1" && rd !== "0") {
                                    originalDescription = rd;
                                    break;
                                }
                            }
                        }


                        var contentTypeLabel = effectiveRaisedEntry
                            ? effectiveRaisedEntry.contentLabel
                            : latestEntry.contentLabel;

                        var declineReason = "";
                        if (declineEntry) {
                            var dr = declineEntry.rawDescription;
                            if (dr && dr !== "0" && dr !== "-1") {
                                var dParts = dr.split("||");
                                if (dParts.length >= 2) {
                                    declineReason = dParts[0].trim();

                                    var declineOrigText = dParts[dParts.length - 1].trim();

                                    if (dParts.length >= 4) {
                                        var dOrigType = dParts[2].trim();
                                        if (dOrigType && dOrigType !== "0" && dOrigType !== "-1") {
                                            var cleanDType = dOrigType.toUpperCase().replace(/ /g, "");
                                            if (CONTENT_LABEL[cleanDType]) {
                                                contentTypeLabel = CONTENT_LABEL[cleanDType];
                                            } else if (cleanDType === "EXTERNALCONTENT") {
                                                contentTypeLabel = "External Resource";
                                            } else {
                                                contentTypeLabel = dOrigType;
                                            }
                                        }
                                    }

                                    if ((!originalDescription || originalDescription === dr) &&
                                        declineOrigText &&
                                        declineOrigText !== "-1" &&
                                        declineOrigText !== "0") {
                                        originalDescription = declineOrigText;
                                    }
                                } else {
                                    declineReason = dr;
                                }
                            }
                        }

                        var responseLink = null;
                        var contentName = null;
                        var materialId = null;
                        var responseContextText = "";
                        var responseEntries = [];

                        var serverAcceptByRid = {};
                        rawList.forEach(function (r) {
                            if (!r || typeof r !== "object") return;
                            var rawRid = (r.REQUEST_ID !== undefined ? r.REQUEST_ID : (r.reqId !== undefined ? r.reqId : r.REQID));
                            if (rawRid === undefined || rawRid === null) return;
                            var ridKey = String(rawRid);
                            if (ridKey !== String(rid)) return;
                            var rawActionVal = (r.ACTION !== undefined ? r.ACTION : r.actionStatus);
                            var actionStr = (ACTION_MAP[rawActionVal] || rawActionVal || "").toString().toUpperCase();
                            if (actionStr !== "ACCEPT" && actionStr !== "COMPLETED") return;
                            var rawMtVal = (r.MATERIAL_TYPE !== undefined ? r.MATERIAL_TYPE : r.materialType);
                            var matStr = (MATERIAL_MAP[rawMtVal] || rawMtVal || "").toString().toUpperCase();
                            var tVal = Number(r.TIME || r.time || 0);
                            if (!serverAcceptByRid.t || tVal > serverAcceptByRid.t) {
                                serverAcceptByRid = { t: tVal, materialType: matStr };
                            }
                        });

                        if (acceptEntries.length > 0) {
                            responseEntries = acceptEntries.map(function (ae) {
                                var det = handle.parseAcceptEntryDetails(ae, contentTypeLabel, CONTENT_LABEL);
                                var effectiveMat = ae.materialType;
                                if (serverAcceptByRid.t &&
                                    Number(ae.rawTime) === Number(serverAcceptByRid.t) &&
                                    serverAcceptByRid.materialType) {
                                    effectiveMat = serverAcceptByRid.materialType;
                                }
                                var fromMaterial = CONTENT_LABEL[effectiveMat];
                                var adminMatLabel = fromMaterial || det.contentTypeLabel || ae.contentLabel;
                                return {
                                    rawTime: ae.rawTime,
                                    date: handle.formatRequestTime(ae.rawTime),
                                    responseLink: det.responseLink,
                                    contentName: det.contentName,
                                    materialId: det.materialId,
                                    responseContextText: det.responseContextText,
                                    contentTypeLabel: adminMatLabel,
                                    materialType: effectiveMat,
                                    spaceId: ae.spaceId
                                };
                            });

                            var latestDet = responseEntries[responseEntries.length - 1];
                            responseLink = latestDet.responseLink;
                            contentName = latestDet.contentName;
                            materialId = latestDet.materialId;
                            responseContextText = latestDet.responseContextText;

                            if ((!originalDescription || originalDescription === acceptEntry.rawDescription) &&
                                responseContextText &&
                                responseContextText !== "-1" &&
                                responseContextText !== "0") {
                                originalDescription = responseContextText;
                            }
                        }

                        if (originalDescription && originalDescription.indexOf("||") !== -1) {
                            var oSep1 = originalDescription.indexOf("||");
                            var oSep2 = originalDescription.indexOf("||", oSep1 + 2);
                            if (oSep2 !== -1) {
                                var ctx = originalDescription.substring(oSep2 + 2).trim();
                                if (ctx && ctx !== "-1" && ctx !== "0") {
                                    originalDescription = ctx;
                                }
                            }
                        }

                        finalRequests.push({
                            id: String(rid),
                            contentType: contentTypeLabel,
                            originalDescription: originalDescription,
                            originalRequestDate: effectiveRaisedEntry ? handle.formatRequestTime(effectiveRaisedEntry.rawTime) : "",
                            reopenEntries: reopenEntries,
                            declineReason: declineReason,
                            declineTime: declineEntry ? handle.formatRequestTime(declineEntry.rawTime) : "",
                            status: derivedStatus,
                            actionStatus: latestAction,
                            rawTime: latestEntry.rawTime,
                            date: handle.formatRequestTime(latestEntry.rawTime),
                           
                            firstRaisedTime: raisedEntry ? raisedEntry.rawTime : (effectiveRaisedEntry ? effectiveRaisedEntry.rawTime : latestEntry.rawTime),
                           
                            effectiveRaisedTime: effectiveRaisedEntry ? effectiveRaisedEntry.rawTime : (raisedEntry ? raisedEntry.rawTime : latestEntry.rawTime),
                          
                            broadcastSiblings: [{
                                reqId: String(rid),
                                scopeId: String(latestEntry.fetchedScopeId || latestEntry.spaceId || "")
                            }],
                            responseLink: responseLink,
                            materialId: materialId,
                            contentName: contentName,
                            responseContentType: acceptEntry ? (CONTENT_LABEL[acceptEntry.materialType] || acceptEntry.contentLabel || contentTypeLabel) : contentTypeLabel,
                            responseTime: acceptEntry ? handle.formatRequestTime(acceptEntry.rawTime) : "",
                            responseEntries: responseEntries,
                            hasFollowup: reopenEntries.length > 0,
                            isRead: isRead,
                            profileUrl: latestEntry.profileUrl || "",
                            hasResponse: !!acceptEntry,
                            productName: (effectiveRaisedEntry && effectiveRaisedEntry.productName)
                                || latestEntry.productName || "",
                            urlProductName: (effectiveRaisedEntry && effectiveRaisedEntry.urlProductName)
                                || latestEntry.urlProductName || "",
                            pageUrl: (effectiveRaisedEntry && effectiveRaisedEntry.pageUrl)
                                || latestEntry.pageUrl || ""
                        });
                    });

                    var updatedCache = Object.assign({}, requestCache);

                    finalRequests.forEach(function (req) {
                        
                        var cached = Object.assign({}, requestCache[String(req.id)] || {});
                        (req.broadcastSiblings || []).forEach(function (s) {
                            var sib = requestCache[String(s.reqId || "")];
                            if (!sib) return;
                            // Prefer the most-recently edited marker.
                            if (sib.edited && (!cached.editedAt || (sib.editedAt || 0) > (cached.editedAt || 0))) {
                                cached.edited = true;
                                cached.editedAt = sib.editedAt || cached.editedAt || 0;
                                if (sib.originalDescription) cached.originalDescription = sib.originalDescription;
                                if (sib.contentType) cached.contentType = sib.contentType;
                                if (sib.originalRequestTime) cached.originalRequestTime = sib.originalRequestTime;
                            } else if (sib.edited && !cached.edited) {
                                cached.edited = true;
                                cached.editedAt = sib.editedAt || 0;
                            }
                            if (sib.lastFollowupEdited) {
                                var sm = sib.lastFollowupEdited;
                                var cm = cached.lastFollowupEdited;
                                if (!cm || (sm.editedAt || 0) > (cm.editedAt || 0)) {
                                    cached.lastFollowupEdited = sm;
                                }
                            }
                            if (Array.isArray(sib.droppedFollowupTimes) && sib.droppedFollowupTimes.length) {
                                var merged = (cached.droppedFollowupTimes || []).slice();
                                sib.droppedFollowupTimes.forEach(function (dt) {
                                    if (merged.indexOf(dt) === -1) merged.push(dt);
                                });
                                cached.droppedFollowupTimes = merged;
                            }
                        });

                        if ((!req.originalDescription || !String(req.originalDescription).trim()) &&
                            cached.originalDescription) {
                            req.originalDescription = cached.originalDescription;
                        }

           
                        if (cached.contentType) {
                            req.contentType = cached.contentType;
                        } else {
                         
                            var pendingType = handle.findPendingContentType(
                                req.originalDescription,
                                req.rawTime
                            );
                            if (pendingType) {
                                req.contentType = pendingType;
                            }
                        }

                        if (!req.productName && cached.productName) {
                            req.productName = cached.productName;
                        }
                        if (!req.urlProductName && cached.urlProductName) {
                            req.urlProductName = cached.urlProductName;
                        }

                     
                        if (cached.edited) {
                            req.edited = true;
                            if (cached.editedAt) req.editedAt = cached.editedAt;
                        }

                        
                        var droppedFollowupTs = 0;
                        var droppedFollowupSet = {};
                        var cachedDropped = Array.isArray(cached.droppedFollowupTimes)
                            ? cached.droppedFollowupTimes : [];
                        cachedDropped.forEach(function (dt) {
                            var n = Number(dt) || 0;
                            if (n) droppedFollowupSet[String(n)] = true;
                        });
                        if (cached.lastFollowupEdited &&
                            Array.isArray(req.reopenEntries) &&
                            req.reopenEntries.length) {
                            var marker = cached.lastFollowupEdited;
                            var prevTs = Number(marker.prevRawTime) || 0;
                            var newTs = Number(marker.newRawTime) || 0;
                            var hasNewEntry = newTs && req.reopenEntries.some(function (re) {
                                return Number(re.rawTime) === newTs;
                            });
                            if (hasNewEntry && prevTs) {
                                droppedFollowupSet[String(prevTs)] = true;
                                droppedFollowupTs = prevTs;
                            }
                            if (Object.keys(droppedFollowupSet).length) {
                                req.reopenEntries = req.reopenEntries.filter(function (re) {
                                    return !droppedFollowupSet[String(Number(re.rawTime) || 0)];
                                });
                            }
                            var matchedIdx = -1;
                            for (var lf = req.reopenEntries.length - 1; lf >= 0; lf--) {
                                var t = Number(req.reopenEntries[lf].rawTime) || 0;
                                if (t === newTs || t === prevTs) {
                                    matchedIdx = lf; break;
                                }
                            }
                            if (matchedIdx === -1) {
                                matchedIdx = req.reopenEntries.length - 1;
                            }
                            if (req.reopenEntries[matchedIdx]) {
                                req.reopenEntries[matchedIdx] = Object.assign(
                                    {}, req.reopenEntries[matchedIdx],
                                    { edited: true, editedAt: marker.editedAt || 0 }
                                );
                            }
                            req.hasFollowup = req.reopenEntries.length > 0;
                        } else if (Object.keys(droppedFollowupSet).length &&
                            Array.isArray(req.reopenEntries) &&
                            req.reopenEntries.length) {
                            req.reopenEntries = req.reopenEntries.filter(function (re) {
                                return !droppedFollowupSet[String(Number(re.rawTime) || 0)];
                            });
                            req.hasFollowup = req.reopenEntries.length > 0;
                        }
                        function isDroppedFollowupTs(ts) {
                            var n = Number(ts) || 0;
                            return !!(n && droppedFollowupSet[String(n)]);
                        }

                        if ((!req.originalRequestDate || req.originalRequestDate === "") &&
                            cached.originalRequestTime) {
                            req.originalRequestDate =
                                handle.formatRequestTime(cached.originalRequestTime);
                        }

                        var cachedFollowups = Array.isArray(cached.followups)
                            ? cached.followups : [];
                        if (cachedFollowups.length) {
                            var seen = {};
                            (req.reopenEntries || []).forEach(function (re) {
                                seen[String(re.rawTime)] = true;
                            });
                            cachedFollowups.forEach(function (fu) {
                                var ts = Number(fu.rawTime) || 0;
                                if (!ts || seen[String(ts)]) return;
                                if (isDroppedFollowupTs(ts)) return;
                                req.reopenEntries.push({
                                    action: "REOPEN",
                                    materialType: "BANNER",
                                    contentLabel: req.contentType || "Guide",
                                    rawDescription: String(fu.description || ""),
                                    rawMaterialId: "0",
                                    rawTime: ts,
                                    date: handle.formatRequestTime(ts),
                                    spaceId: "",
                                    profileUrl: ""
                                });
                            });
                            req.reopenEntries.sort(function (a, b) {
                                return (a.rawTime || 0) - (b.rawTime || 0);
                            });
                            req.hasFollowup = req.reopenEntries.length > 0;
                        }

                        var toCache = updatedCache[String(req.id)] || {};
                        if (req.originalDescription) {
                            toCache.originalDescription = req.originalDescription;
                        }
                        if (req.contentType) {
                            toCache.contentType = req.contentType;
                        }
                        if (req.productName && !toCache.productName) {
                            toCache.productName = req.productName;
                        }
                        if (req.urlProductName && !toCache.urlProductName) {
                            toCache.urlProductName = req.urlProductName;
                        }
                        if (req.pageUrl && !toCache.pageUrl) {
                            toCache.pageUrl = req.pageUrl;
                        }
                        // Restore pageUrl from cache when server omits URL_CHAR.
                        if (!req.pageUrl && cached.pageUrl) {
                            req.pageUrl = cached.pageUrl;
                        }
                        if (req.edited) {
                            toCache.edited = true;
                            if (req.editedAt) toCache.editedAt = req.editedAt;
                        }
                        var earliestServerTs = 0;
                        if (req.reopenEntries && req.reopenEntries.length) {
                            earliestServerTs = req.reopenEntries.reduce(function (acc, re) {
                                var t = Number(re.rawTime) || 0;
                                return (acc === 0 || (t && t < acc)) ? t : acc;
                            }, 0);
                        }
                        var candidateTimes = [
                            Number(toCache.originalRequestTime) || 0,
                            cached.originalRequestTime || 0,
                            earliestServerTs
                        ].filter(function (t) { return t > 0; });
                        if (candidateTimes.length) {
                            toCache.originalRequestTime = Math.min.apply(null, candidateTimes);
                            if (!req.originalRequestDate) {
                                req.originalRequestDate =
                                    handle.formatRequestTime(toCache.originalRequestTime);
                            }
                        }
                        var fuMap = {};
                        (cachedFollowups || []).forEach(function (f) {
                            var fts = Number(f.rawTime) || 0;
                            if (!fts) return;
                            if (isDroppedFollowupTs(fts)) return;
                            fuMap[String(fts)] = {
                                description: String(f.description || ""),
                                rawTime: fts
                            };
                        });
                        (req.reopenEntries || []).forEach(function (re) {
                            if (!re.rawTime || !re.rawDescription) return;
                            if (isDroppedFollowupTs(re.rawTime)) return;
                            fuMap[String(re.rawTime)] = {
                                description: String(re.rawDescription),
                                rawTime: Number(re.rawTime)
                            };
                        });
                        var mergedFollowups = Object.keys(fuMap).map(function (k) {
                            return fuMap[k];
                        }).sort(function (a, b) {
                            return (a.rawTime || 0) - (b.rawTime || 0);
                        });
                        if (mergedFollowups.length) toCache.followups = mergedFollowups;

                        var allDropped = Object.keys(droppedFollowupSet).map(function (k) {
                            return Number(k);
                        }).filter(function (n) { return n > 0; });
                        if (allDropped.length) {
                            toCache.droppedFollowupTimes = allDropped;
                        }

                        if (Object.keys(toCache).length) {
                            updatedCache[String(req.id)] = toCache;
                        }
                    });

                    handle.writeRequestCache(updatedCache);

                    finalRequests.sort(function (a, b) { return b.rawTime - a.rawTime; });

                   
                    var groupedByKey = {};
                    var keyOrder = [];
                    finalRequests.forEach(function (r) {
                    
                        var desc = String(r.originalDescription || "")
                            .trim().toLowerCase().replace(/\s+/g, " ");
                        var hourBucket = Math.floor(
                            (Number(r.firstRaisedTime) || Number(r.rawTime) || 0) / 3600000
                        );
                        var key = desc
                            ? ("D|" + desc + "|" + hourBucket)
                            : ("T|" + hourBucket + "|" + String(r.contentType || "") + "|" + r.id);
                        if (!groupedByKey[key]) {
                            groupedByKey[key] = [];
                            keyOrder.push(key);
                        }
                        groupedByKey[key].push(r);
                    });

                    finalRequests = keyOrder.map(function (key) {
                        var group = groupedByKey[key];
                        if (group.length === 1) return group[0];

                       
                        var STATUS_RANK = {
                            "completed": 4, "remarked": 3,
                            "declined": 2, "open": 1
                        };
                        var base = group.slice().sort(function (a, b) {
                            
                            var sa = (STATUS_RANK[a.status] || 0) +
                                     (a.hasResponse ? 10 : 0) +
                                     (a.hasFollowup ? 4 : 0);
                            var sb = (STATUS_RANK[b.status] || 0) +
                                     (b.hasResponse ? 10 : 0) +
                                     (b.hasFollowup ? 4 : 0);
                            if (sb !== sa) return sb - sa;
                            var ea = (a.effectiveRaisedTime || a.rawTime || 0);
                            var eb = (b.effectiveRaisedTime || b.rawTime || 0);
                            return eb - ea; // tiebreaker: freshest edit
                        })[0];

                       
                        var responder = group.find(function (r) {
                            return r.hasResponse && Array.isArray(r.responseEntries) && r.responseEntries.length;
                        }) || null;
                        var declineSrc = group.find(function (r) {
                            return r.status === "declined" && r.declineReason;
                        }) || null;

                        
                        var mergedResponses = [];
                        var seenResp = {};
                        var mergedReopens = [];
                        var seenReop = {};
                        var mergedSiblings = [];
                        var seenSibling = {};
                        group.forEach(function (r) {
                            (r.responseEntries || []).forEach(function (re) {
                                var k = (re.rawTime || 0) + "|" + (re.rawDescription || "");
                                if (seenResp[k]) return;
                                seenResp[k] = true;
                                mergedResponses.push(re);
                            });
                            (r.reopenEntries || []).forEach(function (re) {
                                var k = (re.rawTime || 0) + "|" + (re.rawDescription || "");
                                if (seenReop[k]) return;
                                seenReop[k] = true;
                                mergedReopens.push(re);
                            });
                            (r.broadcastSiblings || []).forEach(function (s) {
                          
                                var k = String(s.reqId || "");
                                if (!k || seenSibling[k]) return;
                                seenSibling[k] = true;
                                mergedSiblings.push(s);
                            });
                        });
                        mergedResponses.sort(function (a, b) { return (a.rawTime || 0) - (b.rawTime || 0); });
                        mergedReopens.sort(function (a, b) { return (a.rawTime || 0) - (b.rawTime || 0); });

                        return Object.assign({}, base, {
                            responseEntries: mergedResponses,
                            reopenEntries: mergedReopens,
                            broadcastSiblings: mergedSiblings,
                            hasResponse: base.hasResponse || group.some(function (r) { return r.hasResponse; }),
                            hasFollowup: base.hasFollowup || mergedReopens.length > 0,
                            // If any sibling has a response/decline, copy its
                            // response-specific fields over so the surviving
                            // card renders the response section regardless of
                            // which sub-product workspace the admin replied
                            // from.
                            status: (responder ? responder.status : (declineSrc ? declineSrc.status : base.status)),
                            actionStatus: (responder ? responder.actionStatus : (declineSrc ? declineSrc.actionStatus : base.actionStatus)),
                            responseTime: (responder && responder.responseTime) || base.responseTime || "",
                            responseLink: (responder && responder.responseLink) || base.responseLink || "",
                            responseContentType: (responder && responder.responseContentType) || base.responseContentType || "",
                            responseContextText: (responder && responder.responseContextText) || base.responseContextText || "",
                            contentName: (responder && responder.contentName) || base.contentName || "",
                            contentTypeLabel: base.contentTypeLabel || (responder && responder.contentTypeLabel) || "",
                            declineReason: (declineSrc && declineSrc.declineReason) || base.declineReason || "",
                            declineTime: (declineSrc && declineSrc.declineTime) || base.declineTime || ""
                        });
                    });

                    handle.helphubRequests = finalRequests;
                    handle.unviewedRequestCount = unviewedCount;

                } catch (e) {
                    handle.helphubRequests = [];
                }
                handle.updateRequestContentBadge();
        }
    }

    fetchAndUpdateRequestBadge() {
        this.loadUserPastRequests();
    }

    formatRequestTime(timestamp) {
        var ts = Number(timestamp) || timestamp;
        var date = new Date(ts);
        var now = new Date();
        var isToday =
            date.getDate() === now.getDate() &&
            date.getMonth() === now.getMonth() &&
            date.getFullYear() === now.getFullYear();
        var hours = date.getHours();
        var minutes = date.getMinutes().toString().padStart(2, "0");
        var ampm = hours >= 12 ? "PM" : "AM";
        var displayHours = hours % 12 || 12;
        var timeStr = displayHours + "." + minutes + ampm;
        if (isToday) return "Today, " + timeStr;
        var month = date.toLocaleString("default", { month: "short" });
        return month + " " + date.getDate() + ", " + timeStr;
    }

    updateRequestContentBadge() {
        var badge = this.findInWidget("helphub-request-badge");
        if (!badge) return;
        if (this.unviewedRequestCount > 0) {
            badge.style.display = "flex";
            badge.innerText = this.unviewedRequestCount;
        } else {
            badge.style.display = "none";
        }
    }

    clearRequestContentBadge() {
        this.unviewedRequestCount = 0;
        localStorage.setItem("helphub_last_viewed", String(Date.now()));
        var badge = this.findInWidget("helphub-request-badge");
        if (badge) badge.style.display = "none";
    }

    injectRequestContentButton() {
        var handle = this;
        var topbar = handle.findInWidget("topbar");
        if (!topbar) return;
        var closeIcon = handle.findInWidget("micsselfhelpclosableIcon");

        var topbarColor = topbar.style.color || "#ffffff";

        var btnWrapper = document.createElement("div");
        btnWrapper.id = "helphub-request-btn-area";
        btnWrapper.innerHTML = `
      <div id="helphub-request-content-btn" style="background:transparent;color:${topbarColor};border:1px solid rgba(255,255,255,0.5);border-radius:4px;padding:3px 10px;font-size:11px;cursor:pointer;display:inline-flex;align-items:center;gap:5px;white-space:nowrap;font-family:inherit;line-height:1.5;position:relative;margin-right:8px;transition:box-shadow .2s ease,transform .2s ease,background .2s ease;">
        Request Content
        <span id="helphub-request-badge" style="display:none;background:#e53935;color:#fff;border-radius:50%;width:17px;height:17px;font-size:10px;align-items:center;justify-content:center;font-weight:700;flex-shrink:0;line-height:1;position:absolute;top:-8px;right:-8px;box-shadow:0 1px 4px rgba(0,0,0,0.3);">0</span>
      </div>`;

        topbar.style.display = "flex";
        topbar.style.alignItems = "center";
        topbar.style.justifyContent = "space-between";

        var rightGroup = document.createElement("div");
        rightGroup.id = "helphub-topbar-right";
        rightGroup.style.cssText = "display:inline-flex;align-items:center;gap:4px;margin-left:auto;";
        topbar.appendChild(rightGroup);
        rightGroup.appendChild(btnWrapper);
        rightGroup.appendChild(closeIcon);

        var finalBtn = handle.findInWidget("helphub-request-content-btn");
        finalBtn.addEventListener("mouseenter", function () {
            this.style.boxShadow = "0 4px 16px rgba(0,0,0,0.28)";
            this.style.transform = "translateY(-1px)";
            this.style.background = "rgba(255,255,255,0.12)";
        });
        finalBtn.addEventListener("mouseleave", function () {
            this.style.boxShadow = "none";
            this.style.transform = "translateY(0)";
            this.style.background = "transparent";
        });
        finalBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            handle.clearRequestContentBadge();
            var existing = handle.findInWidget("helphub-request-panel");
            if (existing) {
                handle.renderRequestsList();
                handle.attachListEventListeners();
                return;
            }
            handle.showRequestContentPanel();
        });
    }

    showRequestContentPanel() {
        var handle = this;
        var container = handle.getWidgetRoot();
        if (!container) return;

        handle.clearRequestContentBadge();
        container.style.position = "absolute";
        container.style.overflow = "hidden";

        var topbarEl = handle.findInWidget("topbar");
        var topbarBg = topbarEl ? window.getComputedStyle(topbarEl).backgroundColor : "#003297";
        var topbarColor = topbarEl ? window.getComputedStyle(topbarEl).color : "#ffffff";
        var topbarHeight = topbarEl ? topbarEl.offsetHeight : 45;

        var panel = document.createElement("div");
        panel.id = "helphub-request-panel";
        panel.style.cssText = "top:" + topbarHeight + "px;";
        panel.innerHTML = `
      <div id="helphub-panel-header-row">
        <span id="helphub-panel-back-btn">&#8592; Back</span>
      </div>
      <div id="helphub-panel-body">
        <div id="helphub-requests-list"></div>
      </div>
      <div id="helphub-panel-footer">
        <div id="helphub-add-request-btn" style="background:${topbarBg};color:${topbarColor};">
          <span class="helphub-plus-icon">+</span> Add a New Request
        </div>
      </div>`;

        container.appendChild(panel);

        handle.renderRequestsList();
        handle.attachListEventListeners();

        panel.querySelector("#helphub-panel-back-btn").addEventListener("click", function () {
            panel.remove();
            handle.requestPanelVisible = false;
            container.style.overflow = "";
        });
        var addBtn = panel.querySelector("#helphub-add-request-btn");
        if (addBtn) {
            addBtn.addEventListener("click", function () {
                handle.showNewRequestForm(panel);
            });
        }
    }

    showInlinePanelMessage(containerEl, message, type) {
        var existing = containerEl.querySelector(".helphub-inline-msg");
        if (existing) existing.remove();
        var msg = document.createElement("div");
        msg.className = "helphub-inline-msg helphub-inline-msg--" + (type || "error");
        msg.innerText = message;
        containerEl.appendChild(msg);
    }


    renderRequestsList() {
        var handle = this;
        var listDiv = handle.findInWidget("helphub-requests-list");
        if (!listDiv) return;


        var topbarEl = handle.findInWidget("topbar");
        var topbarBg = topbarEl ? window.getComputedStyle(topbarEl).backgroundColor : "#1a56db";
        var topbarColor = topbarEl ? window.getComputedStyle(topbarEl).color : "#ffffff";

        // Show only requests that belong to the currently-active product.
        // For non-bundle workspaces, every request is shown.
        var activeMeta = handle.getActiveProductMeta();
        var visibleRequests = (handle.helphubRequests || []).filter(function (r) {
            return handle.isRequestForActiveProduct(r, activeMeta);
        });

        if (!visibleRequests.length) {
            listDiv.innerHTML = `
            <div class="helphub-empty-state">
              <svg width="38" height="38" viewBox="0 0 24 24" fill="none"
                   stroke="#1a56db" stroke-width="1.5">
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
              <div class="helphub-empty-text">
                Looking for specific content?<br>
                <span>Raise a request and we'll get it ready for you.</span>
              </div>
            </div>`;
            return;
        }

        listDiv.innerHTML = "";

        visibleRequests.forEach(function (req) {
            var isOpen = req.status === "open";
            var isCompleted = req.status === "completed";
            var isRemarked = req.status === "remarked";
            var isDeclined = req.status === "declined";

            var hasResponse = !!req.hasResponse;

            var contentLabel = req.contentType || "Guide";

            var badgeClass, statusLabel;
            if (isDeclined) {
                badgeClass = "helphub-badge--declined";
                statusLabel = req.hasFollowup ? "Follow-up declined" : "Request declined";
            } else if (isCompleted) {
                badgeClass = "helphub-badge--handled";
                statusLabel = req.hasFollowup ? "Follow-up handled" : "Request handled";
            } else if (isRemarked) {
                badgeClass = "helphub-badge--remarked";
                statusLabel = "Follow-up sent";
            } else {
                badgeClass = "helphub-badge--open";
                statusLabel = "Open request";
            }

            var card = document.createElement("div");
            card.className = "helphub-thread-card";

            var headerDiv = document.createElement("div");
            headerDiv.className = "helphub-thread-header";
            headerDiv.innerHTML = `
            <span class="helphub-status-badge ${badgeClass}">
              <span class="helphub-status-dot"></span>${statusLabel}
            </span>`;
            card.appendChild(headerDiv);

            var entriesDiv = document.createElement("div");
            entriesDiv.className = "helphub-thread-entries";
            card.appendChild(entriesDiv);

            var descHtml = req.originalDescription
                ? handle.escapeHtml(req.originalDescription)
                : '<span class="helphub-entry-body--empty">No description provided.</span>';

            var showReqEditBtn = isOpen;

            var reqEditBtn = showReqEditBtn
                ? `<div class="helphub-followup-edit-btn" role="button" tabindex="0" data-id="${req.id}" data-target="request">
                     <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                       <path d="M17 3a2.828 2.121 0 1 1 4 4L7.5 20.5 2 22 l1.5-5.5L17 3z"/>
                     </svg>Edit
                   </div>`
                : "";

            var typeTagHtml = `<span class="helphub-content-type-tag">Type: ${handle.escapeHtml(contentLabel)}</span>`;


            var editedTagHtml = req.edited
                ? `<span class="helphub-edited-tag" style="font-size:10px;font-weight:500;color:#888;margin-left:4px;font-style:italic;text-transform:none;letter-spacing:0;">(edited)</span>`
                : "";

            var reqEntry = document.createElement("div");
            reqEntry.className = "helphub-entry-row helphub-entry--request";
            reqEntry.innerHTML = `
            <div class="helphub-entry-label">
              <span class="helphub-entry-label__left helphub-entry-label__left--request">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                   <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>Request${editedTagHtml}
              </span>
              <div style="display:flex;align-items:center;gap:8px;">
                ${reqEditBtn}
                <span class="helphub-entry-date">${req.originalRequestDate || ""}</span>
              </div>
            </div>
            <div id="req-display-${req.id}" class="helphub-entry-body">${descHtml}</div>
            <div id="req-type-tag-${req.id}" class="helphub-entry-type-tag">${typeTagHtml}</div>
            <div id="req-form-${req.id}" style="display:none;margin-top:8px;" data-selected-type="${handle.escapeHtml(req.contentType || "")}">
              <div class="helphub-field-label">Select content type</div>
              <div id="edit-type-dropdown-${req.id}" class="helphub-dropdown-root" style="margin-bottom:8px;">
                <div class="helphub-dropdown-trigger" data-id="${req.id}" data-action="toggle-edit-dropdown">
                  <span id="edit-type-label-${req.id}">${handle.escapeHtml(req.contentType || "Guide")}</span>
                  <svg class="helphub-dropdown-arrow" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="6 9 12 15 18 9"/>
                  </svg>
                </div>
                <div id="edit-type-options-${req.id}" class="helphub-dropdown-options" style="display:none;">
                  <div class="helphub-dropdown-option" data-id="${req.id}" data-action="select-edit-type" data-value="Walkthrough">Walkthrough</div>
                  <div class="helphub-dropdown-option" data-id="${req.id}" data-action="select-edit-type" data-value="Interactivevideo">Interactive Video</div>
                  <div class="helphub-dropdown-option" data-id="${req.id}" data-action="select-edit-type" data-value="Guide">Guide</div>
                </div>
              </div>
              <div class="helphub-field-label">Description</div>
              <textarea id="req-ta-${req.id}" class="helphub-remark-textarea" maxlength="${CHAR_LIMIT}">${handle.escapeHtml(req.originalDescription || "")}</textarea>
              <div style="display:flex;justify-content:space-between;align-items:center;margin-top:4px;">
                <span class="helphub-char-warning" style="display:${(req.originalDescription || "").length >= CHAR_LIMIT ? "inline" : "none"};color:#e53e3e;font-size:11px;font-weight:normal;">Only ${CHAR_LIMIT} characters are allowed.</span>
                <span class="helphub-char-count" style="margin-left:auto;">${(req.originalDescription || "").length} / ${CHAR_LIMIT}</span>
              </div>
              <div id="req-err-${req.id}"></div>
              <div class="helphub-form-actions helphub-form-actions--right">
                <div class="helphub-btn-cancel" role="button" tabindex="0" data-id="${req.id}" data-action="cancel-req-edit">Cancel</div>
                <div class="helphub-btn-send" role="button" tabindex="0" data-id="${req.id}" data-action="save-req-edit"
                        style="background:${topbarBg};color:#fff;">Update</div>
              </div>
            </div>`;
            entriesDiv.appendChild(reqEntry);

            var responseEntries = Array.isArray(req.responseEntries) ? req.responseEntries : [];
            var reopenEntries = Array.isArray(req.reopenEntries) ? req.reopenEntries : [];

            var latestReopenTime = reopenEntries.reduce(function (acc, re) {
                var t = Number(re.rawTime) || 0;
                return t > acc ? t : acc;
            }, 0);
            var visibleResponses = responseEntries.filter(function (re) {
                return (Number(re.rawTime) || 0) > latestReopenTime;
            });

            var timeline = [];
            reopenEntries.forEach(function (re, idx) {
                timeline.push({ kind: "followup", entry: re, idx: idx, rawTime: Number(re.rawTime) || 0 });
            });
            visibleResponses.forEach(function (re, idx) {
                timeline.push({ kind: "response", entry: re, idx: idx, rawTime: Number(re.rawTime) || 0 });
            });
            timeline.sort(function (a, b) { return a.rawTime - b.rawTime; });

            var lastFollowupIdx = reopenEntries.length - 1;

            timeline.forEach(function (item) {
                if (item.kind === "followup") {
                    var reopen = item.entry;
                    var idx = item.idx;
                    var fuRaw = reopen.rawDescription;
                    var fuText = (fuRaw && fuRaw !== "-1" && fuRaw !== "0") ? fuRaw : "";
                    var fuId = req.id + "-fu-" + idx;
                    var isLastFollowup = (idx === lastFollowupIdx);
                    var showFuEditBtn = isRemarked && isLastFollowup;

                    var fuEntry = document.createElement("div");
                    fuEntry.className = "helphub-entry-row helphub-entry--followup";
                    var fuEditedTagHtml = reopen.edited
                        ? `<span class="helphub-edited-tag" style="font-size:10px;font-weight:500;color:#888;margin-left:4px;font-style:italic;text-transform:none;letter-spacing:0;">(edited)</span>`
                        : "";
                    fuEntry.innerHTML = `
                    <div class="helphub-entry-label">
                      <span class="helphub-entry-label__left helphub-entry-label__left--followup">
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                        </svg>Follow-up${fuEditedTagHtml}
                      </span>
                      <div style="display:flex;align-items:center;gap:8px;">
                        ${showFuEditBtn ? `
                        <div class="helphub-followup-edit-btn" role="button" tabindex="0" data-fu-id="${fuId}">
                          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M17 3a2.828 2.121 0 1 1 4 4L7.5 20.5 2 22 l1.5-5.5L17 3z"/>
                          </svg>Edit
                        </div>` : ""}
                        <span class="helphub-entry-date">${reopen.date || ""}</span>
                      </div>
                    </div>
                    <div id="fu-display-${fuId}" class="helphub-entry-body">${fuText ? handle.escapeHtml(fuText) : '<span class="helphub-entry-body--empty">No message.</span>'}</div>
                    ${showFuEditBtn ? `
                    <div id="fu-form-${fuId}" style="display:none;margin-top:8px;">
                      <textarea id="fu-ta-${fuId}" class="helphub-remark-textarea" maxlength="${CHAR_LIMIT}">${handle.escapeHtml(fuText)}</textarea>
                      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:4px;">
                        <span class="helphub-char-warning" style="display:${fuText.length >= CHAR_LIMIT ? "inline" : "none"};color:#e53e3e;font-size:11px;font-weight:normal;">Only ${CHAR_LIMIT} characters are allowed.</span>
                        <span class="helphub-char-count" style="margin-left:auto;">${fuText.length} / ${CHAR_LIMIT}</span>
                      </div>
                      <div id="fu-err-${fuId}"></div>
                      <div class="helphub-form-actions helphub-form-actions--right">
                        <div class="helphub-btn-cancel" role="button" tabindex="0" data-fu-id="${fuId}" data-action="cancel-fu-edit">Cancel</div>
                        <div class="helphub-btn-send" role="button" tabindex="0" data-fu-id="${fuId}" data-action="save-fu-edit"
                                style="background:${topbarBg};color:#fff;">Update</div>
                      </div>
                    </div>` : ""}`;
                    entriesDiv.appendChild(fuEntry);
                } else if (item.kind === "response") {
                    var resp = item.entry;
                    var rContentType = resp.contentTypeLabel || contentLabel;
                    var rDisplayName = resp.contentName || rContentType;
                    var rLinkHtml = resp.responseLink
                        ? `<a href="${resp.responseLink}" target="_blank" rel="noopener noreferrer" class="helphub-attached-link">${handle.escapeHtml(rDisplayName)}</a>`
                        : `<strong>${handle.escapeHtml(rDisplayName)}</strong>`;

                    var respEntry = document.createElement("div");
                    respEntry.className = "helphub-entry-row helphub-entry--response";
                    respEntry.innerHTML = `
                    <div class="helphub-entry-label">
                      <span class="helphub-entry-label__left helphub-entry-label__left--response">
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                          <polyline points="20 6 9 17 4 12"/>
                        </svg>Response handled
                      </span>
                      <span class="helphub-entry-date">${resp.date || ""}</span>
                    </div>
                    <div class="helphub-entry-body">Your request has been handled.</div>
                    <div class="helphub-attached-block">
                      <div class="helphub-attached-title">Attached content</div>
                      <div class="helphub-attached-row">
                        <span class="helphub-attached-key">Content type</span>
                        <span class="helphub-attached-val">${rContentType}</span>
                      </div>
                      <div class="helphub-attached-row">
                        <span class="helphub-attached-key">Content</span>
                        <span class="helphub-attached-val">${rLinkHtml}</span>
                      </div>
                    </div>`;
                    entriesDiv.appendChild(respEntry);
                }
            });

            if (hasResponse && isCompleted) {
                var reopenFooter = document.createElement("div");
                reopenFooter.className = "helphub-thread-footer";
                reopenFooter.id = "reopen-footer-" + req.id;
                reopenFooter.innerHTML = `
                <div class="helphub-reopen-btn" role="button" tabindex="0" data-id="${req.id}" data-action="show-reopen">
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15 l-4 1 1-4 9.5-9.5z"/>
                  </svg>
                  Reopen request
                </div>`;
                card.appendChild(reopenFooter);

                var reopenFormWrap = document.createElement("div");
                reopenFormWrap.innerHTML = `
                <div class="helphub-remark-form-wrap" id="remark-section-${req.id}" style="display:none;">
                  <div class="helphub-remark-form-title">
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                    </svg>Follow-up request
                  </div>
                  <textarea id="remark-ta-${req.id}" class="helphub-remark-textarea helphub-remark-textarea--tall"
                            placeholder="Describe your follow-up..." maxlength="${CHAR_LIMIT}"></textarea>
                  <div class="helphub-form-row" style="display:flex;justify-content:space-between;align-items:center;margin-top:4px;">
                    <span class="helphub-char-warning" style="display:none;color:#e53e3e;font-size:11px;font-weight:normal;">Only ${CHAR_LIMIT} characters are allowed.</span>
                    <span class="helphub-char-count" style="margin-left:auto;">0 / ${CHAR_LIMIT}</span>
                  </div>
                  <div id="remark-err-${req.id}"></div>
                  <div class="helphub-form-actions helphub-form-actions--right">
                    <div class="helphub-btn-cancel" role="button" tabindex="0" data-id="${req.id}" data-action="cancel-reopen">Cancel</div>
                    <div class="helphub-btn-send" role="button" tabindex="0" data-id="${req.id}" data-action="send-reopen"
                            style="background:${topbarBg};color:#fff;">Send</div>
                  </div>
                </div>`;
                card.appendChild(reopenFormWrap);
            }

            if (isDeclined) {
                var decEntry = document.createElement("div");
                decEntry.className = "helphub-entry-row helphub-entry--declined";
                decEntry.innerHTML = `
                <div class="helphub-entry-label">
                  <span class="helphub-entry-label__left helphub-entry-label__left--declined">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                      <circle cx="12" cy="12" r="10"/>
                      <line x1="15" y1="9" x2="9" y2="15"/>
                      <line x1="9" y1="9" x2="15" y2="15"/>
                    </svg>Response
                  </span>
                  <span class="helphub-entry-date">${req.declineTime || req.date || ""}</span>
                </div>
                <div class="helphub-entry-body helphub-entry-body--declined">
                  ${handle.escapeHtml(req.declineReason) || '<span class="helphub-entry-body--empty">No reason provided.</span>'}
                </div>`;
                entriesDiv.appendChild(decEntry);
            }

            listDiv.appendChild(card);
        });
    }

    attachListEventListeners() {
        var handle = this;
        var listDiv = handle.findInWidget("helphub-requests-list");
        if (!listDiv || listDiv.dataset.listenersAttached) return;
        listDiv.dataset.listenersAttached = "true";

        listDiv.addEventListener("click", function (e) {
            var btn = e.target.closest("[data-action]");
            if (!btn) return;
            var action = btn.dataset.action;
            var id = btn.dataset.id;
            var fuId = btn.dataset.fuId;

            switch (action) {
                case "show-reopen": {
                    var sec = handle.findInWidget("remark-section-" + id);
                    var ftr = handle.findInWidget("reopen-footer-" + id);
                    if (sec) sec.style.display = "block";
                    if (ftr) ftr.style.display = "none";
                    var ta = handle.findInWidget("remark-ta-" + id);
                    if (ta) ta.focus();
                    break;
                }
                case "cancel-reopen": {
                    var sec = handle.findInWidget("remark-section-" + id);
                    var ftr = handle.findInWidget("reopen-footer-" + id);
                    if (sec) sec.style.display = "none";
                    if (ftr) ftr.style.display = "flex";
                    var ta = handle.findInWidget("remark-ta-" + id);
                    if (ta) ta.value = "";
                    var errEl = handle.findInWidget("remark-err-" + id);
                    if (errEl) errEl.innerHTML = "";
                    break;
                }
                case "send-reopen": {
                    var ta = handle.findInWidget("remark-ta-" + id);
                    var err = handle.findInWidget("remark-err-" + id);
                    var text = ta ? ta.value.trim() : "";
                    if (!text) {
                        if (err) handle.showInlinePanelMessage(err, "Please describe the reason before sending.", "error");
                        return;
                    }
                    handle.submitRemark(id, text);
                    break;
                }
                case "cancel-req-edit": {
                    var disp = handle.findInWidget("req-display-" + id);
                    var tag = handle.findInWidget("req-type-tag-" + id);
                    var form = handle.findInWidget("req-form-" + id);
                    if (disp) disp.style.display = "block";
                    if (tag) tag.style.display = "inline-flex";
                    if (form) form.style.display = "none";
                    break;
                }
                case "save-req-edit": {
                    var ta = handle.findInWidget("req-ta-" + id);
                    var err = handle.findInWidget("req-err-" + id);
                    var form = handle.findInWidget("req-form-" + id);
                    var text = ta ? ta.value.trim() : "";
                    var type = form ? form.dataset.selectedType : "";
                   
                    if (!type) {
                        var existingReq = (handle.helphubRequests || []).find(function (r) {
                            return String(r.id) === String(id);
                        });
                        type = (existingReq && existingReq.contentType) ? existingReq.contentType : "Guide";
                    }
                    if (!text) {
                        if (err) handle.showInlinePanelMessage(err, "Description cannot be empty.", "error");
                        return;
                    }
                    var disp = handle.findInWidget("req-display-" + id);
                    if (disp) { disp.innerText = text; disp.style.display = "block"; }
                    if (form) form.style.display = "none";
                    handle.updateUserRequest(id, text, type);
                    break;
                }
                case "toggle-edit-dropdown": {
                    var opt = handle.findInWidget("edit-type-options-" + id);
                    if (opt) opt.style.display = (opt.style.display === "none") ? "block" : "none";
                    break;
                }
                case "select-edit-type": {
                    var val = btn.dataset.value;
                    var label = handle.findInWidget("edit-type-label-" + id);
                    var form = handle.findInWidget("req-form-" + id);
                    var opt = handle.findInWidget("edit-type-options-" + id);
                    if (label) label.innerText = (val === "Interactivevideo" ? "Interactive Video" : (val === "Externalresource" ? "External Resource" : val));
                    if (form) form.dataset.selectedType = val;
                    if (opt) opt.style.display = "none";
                    break;
                }
                case "cancel-fu-edit": {
                    var disp = handle.findInWidget("fu-display-" + fuId);
                    var form = handle.findInWidget("fu-form-" + fuId);
                    if (disp) disp.style.display = "block";
                    if (form) form.style.display = "none";
                    break;
                }
                case "save-fu-edit": {
                    var ta = handle.findInWidget("fu-ta-" + fuId);
                    var err = handle.findInWidget("fu-err-" + fuId);
                    var text = ta ? ta.value.trim() : "";
                    if (!text) {
                        if (err) handle.showInlinePanelMessage(err, "Follow-up cannot be empty.", "error");
                        return;
                    }
                    var disp = handle.findInWidget("fu-display-" + fuId);
                    var form = handle.findInWidget("fu-form-" + fuId);
                    if (disp) { disp.innerText = text; disp.style.display = "block"; }
                    if (form) form.style.display = "none";
                    var parts = fuId.split("-fu-");
                    var reqId = parts[0];
                    var idx = parseInt(parts[1], 10);
                    var nowTs = Date.now();
                    var prevServerTs = 0;
                    var existingReqBefore = (handle.helphubRequests || []).find(function (r) {
                        return String(r.id) === String(reqId);
                    });
                    if (existingReqBefore &&
                        Array.isArray(existingReqBefore.reopenEntries) &&
                        existingReqBefore.reopenEntries[idx]) {
                        prevServerTs = Number(existingReqBefore.reopenEntries[idx].rawTime) || 0;
                    }
                    handle.helphubRequests = handle.helphubRequests.map(function (r) {
                        if (r.id !== reqId) return r;
                        var updatedReopens = r.reopenEntries.map(function (re, i) {
                            return i === idx ? Object.assign({}, re, {
                                rawDescription: text,
                                rawTime: nowTs,
                                date: handle.formatRequestTime(nowTs),
                                edited: true,
                                editedAt: nowTs
                            }) : re;
                        });
                        return Object.assign({}, r, {
                            reopenEntries: updatedReopens,
                            rawTime: nowTs,
                            date: handle.formatRequestTime(nowTs)
                        });
                    });
                    handle.helphubRequests.sort(function (a, b) { return b.rawTime - a.rawTime; });
                    handle.renderRequestsList();
                    handle.attachListEventListeners();
                    handle.cacheFollowup(reqId, text, nowTs);
                    handle.updateUserFollowup(reqId, text, prevServerTs, nowTs);
                    break;
                }
            }
        });

        listDiv.addEventListener("click", function (e) {
            var reqEditBtn = e.target.closest(".helphub-followup-edit-btn[data-id]");
            if (reqEditBtn && reqEditBtn.dataset.target === "request") {
                var id = reqEditBtn.dataset.id;
                var disp = handle.findInWidget("req-display-" + id);
                var tag = handle.findInWidget("req-type-tag-" + id);
                var form = handle.findInWidget("req-form-" + id);
                if (disp) disp.style.display = "none";
                if (tag) tag.style.display = "none";
                if (form) form.style.display = "block";
                var ta = handle.findInWidget("req-ta-" + id);
                if (ta) {
                    handle.autoGrowTextarea(ta);
                    ta.focus();
                    ta.setSelectionRange(ta.value.length, ta.value.length);
                }
                return;
            }
            var fuEditBtn = e.target.closest(".helphub-followup-edit-btn[data-fu-id]");
            if (fuEditBtn) {
                var fuId = fuEditBtn.dataset.fuId;
                var disp = handle.findInWidget("fu-display-" + fuId);
                var form = handle.findInWidget("fu-form-" + fuId);
                if (disp) disp.style.display = "none";
                if (form) form.style.display = "block";
                var ta = handle.findInWidget("fu-ta-" + fuId);
                if (ta) {
                    handle.autoGrowTextarea(ta);
                    ta.focus();
                    ta.setSelectionRange(ta.value.length, ta.value.length);
                }
            }
        });

        listDiv.addEventListener("input", function (e) {
            var ta = e.target;
            if (ta.tagName === "TEXTAREA") {
                handle.autoGrowTextarea(ta);
                var len = ta.value.length;
                var parent = ta.parentNode;
                if (parent) {
                    var counter = parent.querySelector(".helphub-char-count");
                    if (counter) {
                        counter.textContent = len + " / " + CHAR_LIMIT;
                    }
                    var warning = parent.querySelector(".helphub-char-warning");
                    if (warning) {
                        warning.style.display = len >= CHAR_LIMIT ? "inline" : "none";
                    }
                }
               
                if (ta.id && len > 0) {
                    var errId = null;
                    if (ta.id.indexOf("remark-ta-") === 0) {
                        errId = "remark-err-" + ta.id.substring("remark-ta-".length);
                    } else if (ta.id.indexOf("fu-ta-") === 0) {
                        errId = "fu-err-" + ta.id.substring("fu-ta-".length);
                    } else if (ta.id.indexOf("req-ta-") === 0) {
                        errId = "req-err-" + ta.id.substring("req-ta-".length);
                    }
                    if (errId) {
                        var errEl = handle.findInWidget(errId);
                        if (errEl) errEl.innerHTML = "";
                    }
                }
            }
        });
    }

    autoGrowTextarea(ta) {
        if (!ta || ta.tagName !== "TEXTAREA") return;
        // Reset so we can measure the natural content height.
        ta.style.height = "auto";
        var next = ta.scrollHeight;

       
        var computedMax = parseInt(window.getComputedStyle(ta).maxHeight, 10);
        if (isNaN(computedMax) || computedMax <= 0) computedMax = 320;

        if (next > computedMax) {
          
            ta.style.height = computedMax + "px";
            ta.style.overflowY = "auto";
        } else {
         
            ta.style.height = next + "px";
            ta.style.overflowY = "hidden";
        }
    }

    escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    showNewRequestForm(panel) {
        var handle = this;
        var body = panel.querySelector("#helphub-panel-body");
        var footer = panel.querySelector("#helphub-panel-footer");
        var headerRow = panel.querySelector("#helphub-panel-header-row");

        var topbarEl = handle.findInWidget("topbar");
        var topbarBg = topbarEl ? window.getComputedStyle(topbarEl).backgroundColor : "#003297";
        var topbarColor = topbarEl ? window.getComputedStyle(topbarEl).color : "#ffffff";

        footer.style.display = "none";
        headerRow.style.display = "none";
        body.style.transition = "opacity 0.2s ease";
        body.style.opacity = "0";

        setTimeout(function () {
            body.innerHTML = `
        <div style="padding:14px 12px;box-sizing:border-box;display:flex;flex-direction:column;">
          <div style="margin-bottom:12px;">
            <label class="helphub-field-label">Select content type</label>
            <div id="helphub-type-dropdown-root" class="helphub-dropdown-root">
              <div id="helphub-type-trigger" class="helphub-dropdown-trigger">
                <span id="helphub-type-label" class="helphub-dropdown-placeholder">choose content type</span>
                <svg class="helphub-dropdown-arrow" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="6 9 12 15 18 9"/>
                </svg>
              </div>
              <div id="helphub-type-options" class="helphub-dropdown-options" style="display:none;">
                <div class="helphub-dropdown-option" data-value="Walkthrough">Walkthrough</div>
                <div class="helphub-dropdown-option" data-value="Interactivevideo">Interactive Video</div>
                <div class="helphub-dropdown-option" data-value="Guide">Guide</div>
              </div>
            </div>
          </div>
          <div class="helphub-form-field">
            <div class="helphub-field-label-row">
              <span class="helphub-field-label">Description</span>
              <span class="helphub-char-count">0 / ${CHAR_LIMIT}</span>
            </div>
            <textarea id="helphub-request-description" class="helphub-remark-textarea helphub-remark-textarea--tall"
              placeholder="Describe the reason..." maxlength="${CHAR_LIMIT}"></textarea>
            <div style="display:flex;justify-content:flex-start;margin-top:4px;">
              <span class="helphub-char-warning" style="display:none;color:#e53e3e;font-size:11px;font-weight:normal;">Only ${CHAR_LIMIT} characters are allowed.</span>
            </div>
          </div>
          <div id="helphub-form-error-area" style="min-height:0;margin-bottom:2px;"></div>
          <div class="helphub-form-actions helphub-form-actions--right">
            <div id="helphub-form-cancel" class="helphub-btn-cancel" role="button" tabindex="0">Cancel</div>
            <div id="helphub-form-send" class="helphub-btn-send" role="button" tabindex="0"
              style="background:${topbarBg};color:${topbarColor};">Send</div>
          </div>
        </div>`;
            body.style.opacity = "1";

            var trigger = body.querySelector("#helphub-type-trigger");
            var optionsList = body.querySelector("#helphub-type-options");
            var typeLabel = body.querySelector("#helphub-type-label");
            var selectedContentType = "";

            function toggleDropdown(show) {
                var open = (show !== undefined) ? show : (optionsList.style.display === "none");
                optionsList.style.display = open ? "block" : "none";
                trigger.style.borderColor = open ? "#4f46e5" : "";
                trigger.style.boxShadow = open ? "0 0 0 2px rgba(79,70,229,.12)" : "none";
            }
            trigger.addEventListener("click", function (e) { e.stopPropagation(); toggleDropdown(); });

            body.querySelectorAll(".helphub-dropdown-option").forEach(function (opt) {
                opt.addEventListener("click", function (e) {
                    e.stopPropagation();
                    selectedContentType = this.getAttribute("data-value");
                    typeLabel.innerText = this.innerText;
                    typeLabel.className = "";
                    typeLabel.style.color = "#2d3748";
                    toggleDropdown(false);
                    var ea = body.querySelector("#helphub-form-error-area");
                    if (ea) ea.innerHTML = "";
                });
            });

            var closeDropdown = function () { toggleDropdown(false); };
            document.addEventListener("click", closeDropdown);

            body.querySelector("#helphub-request-description").addEventListener("input", function () {
                handle.autoGrowTextarea(this);
                var len = this.value.length;
                var counter = body.querySelector(".helphub-char-count");
                if (counter) {
                    counter.textContent = len + " / " + CHAR_LIMIT;
                }
                var warning = body.querySelector(".helphub-char-warning");
                if (warning) {
                    warning.style.display = len >= CHAR_LIMIT ? "inline" : "none";
                }
                var ea = body.querySelector("#helphub-form-error-area");
                if (ea) ea.innerHTML = "";
            });

            function restoreListView() {
                document.removeEventListener("click", closeDropdown);
                body.style.opacity = "0";
                setTimeout(function () {
                    if (footer) footer.style.display = "block";
                    if (headerRow) headerRow.style.display = "flex";
                    body.innerHTML = '<div id="helphub-requests-list"></div>';
                    handle.renderRequestsList();
                    handle.attachListEventListeners();
                    body.style.opacity = "1";
                }, 180);
            }

            body.querySelector("#helphub-form-cancel").addEventListener("click", restoreListView);

            body.querySelector("#helphub-form-send").addEventListener("click", function () {
                var description = body.querySelector("#helphub-request-description").value.trim();
                var errorArea = body.querySelector("#helphub-form-error-area");
                if (!selectedContentType || !description) {
                    if (errorArea) {
                        var msg = !selectedContentType && !description
                            ? "Please select a content type and provide a description."
                            : !selectedContentType
                                ? "Please select a content type."
                                : "Please describe the reason before sending.";
                        handle.showInlinePanelMessage(errorArea, msg, "error");
                    }
                    return;
                }
                document.removeEventListener("click", closeDropdown);
                handle.submitHelpRequest(selectedContentType, description, panel, footer, body, headerRow);
            });
        }, 180);
    }

    submitHelpRequest(contentType, description, panel, footer, body, headerRow) {
        var handle = this;

        
        handle.addPendingSubmission(description, contentType);

        function addLocalRequest(reqId) {
            var newId = String(reqId || Date.now());
            var nowTs = Date.now();
            var localMeta = handle.getActiveProductMeta();
            var currentPageUrl = window.location.href || "";
            handle.cacheRequest(newId, {
                originalDescription: description,
                contentType: contentType,
                originalRequestTime: nowTs,
                productName: (localMeta && localMeta.productName) || "",
                urlProductName: (localMeta && localMeta.urlMeta && localMeta.urlMeta.url_product_name) || "",
                pageUrl: currentPageUrl
            });
            handle.helphubRequests.unshift({
                id: newId,
                contentType: contentType,
                originalDescription: description,
                originalRequestDate: handle.formatRequestTime(nowTs),
                reopenEntries: [],
                declineReason: "",
                status: "open",
                actionStatus: "RAISED",
                rawTime: nowTs,
                date: handle.formatRequestTime(nowTs),
                responseLink: null,
                materialId: null,
                contentName: null,
                hasFollowup: false,
                isRead: true,
                profileUrl: "",
                hasResponse: false,
                productName: (localMeta && localMeta.productName) || "",
                urlProductName: (localMeta && localMeta.urlMeta && localMeta.urlMeta.url_product_name) || "",
                pageUrl: currentPageUrl
            });
        }

        function restoreView() {
            if (body) body.style.opacity = "0";
            setTimeout(function () {
                if (footer) footer.style.display = "block";
                if (headerRow) headerRow.style.display = "flex";
                body.innerHTML = '<div id="helphub-requests-list"></div>';
                handle.renderRequestsList();
                handle.attachListEventListeners();
                if (body) body.style.opacity = "1";
            }, 180);
        }

        var params = {
            action: "addUserRequest",
            pageUrl: window.location.href,
            materialType: (function () {
                var normalized = contentType.toLowerCase().replace(/ /g, "");
                if (normalized === "customwebbanner") return "BANNER";
                if (normalized === "externallink" || normalized === "externalcontent" || normalized === "externalresource") return "EXTERNALRESOURCE";
                return contentType.toUpperCase().replace(/ /g, "");
            })(),
            materialId: "0",
            description: description,
            time: String(Date.now()),
            actionStatus: "RAISED",
            orgid: this.orgid,
            Scope: this.scope
        };

        try {
            var activeMeta = handle.getActiveProductMeta();
            if (activeMeta && activeMeta.workspaceConf) {
                if (activeMeta.productName) {
                    params.product_name = activeMeta.productName;
                    params.url_product_name = activeMeta.urlMeta
                        ? activeMeta.urlMeta.url_product_name
                        : activeMeta.productName;
                }
                if (activeMeta.productUrlPath) {
                    params.product_url_path = activeMeta.productUrlPath;
                }
                if (activeMeta.isBundle) {
                    params.product_type = "bundle";
                    params.parent_product_name = activeMeta.workspaceConf.product_name || "";
                   
                }
            }
        } catch (e) { }

        if (!handle.helphubRequestAPI) {
            try {
                handle.helphubRequestAPI = Micssdktoserver.getinstance(handle.inproductconf, handle.orgid, "helprequest");
            } catch (e) { }
        }
        if (!handle.helphubRequestAPI) {
            addLocalRequest();
            restoreView();
            return;
        }
        handle.helphubRequestAPI.submitHelpRequest(
            params,
            function onsuccess(response) {
                try {
                    var parsed = JSON.parse(response);
                    addLocalRequest(parsed.REQUEST_ID || parsed.reqId);
                } catch (e) {
                    addLocalRequest();
                }
                restoreView();
                try {
                    setTimeout(function () {
                        handle.loadUserPastRequests();
                        setTimeout(function () {
                            if (handle.findInWidget("helphub-requests-list")) {
                                handle.renderRequestsList();
                                handle.attachListEventListeners();
                            }
                        }, 600);
                    }, 400);
                } catch (e) { }
            },
            function onerror() {
                addLocalRequest();
                restoreView();
            }
        );
    }

    submitRemark(requestId, remarkDescription) {
        var handle = this;

        function onComplete() {
            var nowTs = Date.now();
            handle.helphubRequests = handle.helphubRequests.map(function (req) {
                if (req.id != requestId) return req;
                var newReopen = {
                    action: "REOPEN",
                    materialType: (req.reopenEntries && req.reopenEntries.length > 0)
                        ? req.reopenEntries[req.reopenEntries.length - 1].materialType
                        : "BANNER",
                    contentLabel: req.contentType,
                    rawDescription: remarkDescription,
                    rawMaterialId: "0",
                    rawTime: nowTs,
                    date: handle.formatRequestTime(nowTs),
                    spaceId: "",
                    profileUrl: ""
                };
                var updatedReopens = (req.reopenEntries || []).concat([newReopen]);
                return Object.assign({}, req, {
                    status: "remarked",
                    actionStatus: "REOPEN",
                    reopenEntries: updatedReopens,
                    responseEntries: Array.isArray(req.responseEntries) ? req.responseEntries.slice() : [],
                    hasFollowup: true,
                    hasResponse: !!req.hasResponse,
                    rawTime: nowTs,
                    date: handle.formatRequestTime(nowTs)
                });
            });
            handle.helphubRequests.sort(function (a, b) {
                return (b.rawTime || 0) - (a.rawTime || 0);
            });
            handle.renderRequestsList();
            handle.attachListEventListeners();
            try {
                setTimeout(function () {
                    handle.loadUserPastRequests();
                    setTimeout(function () {
                        if (handle.findInWidget("helphub-requests-list")) {
                            handle.renderRequestsList();
                            handle.attachListEventListeners();
                        }
                    }, 600);
                }, 400);
            } catch (e) { }
        }

        var existingReq = (handle.helphubRequests || []).find(function (r) {
            return String(r.id) === String(requestId);
        });
        var preservedType = (existingReq && existingReq.contentType)
            ? (existingReq.contentType.toLowerCase().replace(/ /g, "") === "customwebbanner"
                ? "BANNER"
                : existingReq.contentType.toUpperCase().replace(/ /g, ""))
            : "BANNER";

        var params = {
            action: "updateUserRequestDetails",
            reqId: String(requestId),
            actionStatus: "REOPEN",
            description: remarkDescription,
            materialId: "0",
            materialType: preservedType,
            time: String(Date.now()),
            orgid: this.orgid,
            Scope: this.scope
        };
        handle.applySubProductScope(params);

        onComplete();
        handle.fanoutToBroadcastSiblings(requestId, params);
    }

    updateUserRequest(requestId, newDescription, newContentType) {
        var handle = this;
        var matType = "BANNER";
        if (newContentType) {
            matType = (newContentType.toLowerCase().replace(/ /g, "") === "customwebbanner"
                ? "BANNER"
                : newContentType.toUpperCase().replace(/ /g, ""));
        }
        var params = {
            action: "updateUserRequestDetails",
            reqId: String(requestId),
            actionStatus: "RAISED",
            description: newDescription,
            materialId: "0",
            time: String(Date.now()),
            materialType: matType,
            orgid: this.orgid,
            Scope: this.scope
        };
        handle.applySubProductScope(params);

        function applyEditLocally() {
            handle.cacheRequestForAllSiblings(requestId, {
                originalDescription: newDescription,
                contentType: newContentType,
                originalRequestTime: Number(params.time),
                edited: true,
                editedAt: Number(params.time)
            });
            handle.helphubRequests = handle.helphubRequests.map(function (r) {
                if (r.id === String(requestId)) {
                    return Object.assign({}, r, {
                        originalDescription: newDescription,
                        contentType: newContentType,
                        contentTypeLabel: (newContentType === "Interactivevideo" ? "Interactive Video" : (newContentType === "Externalresource" ? "External Resource" : newContentType)),
                        originalRequestDate: handle.formatRequestTime(params.time),
                        rawTime: Number(params.time),
                        edited: true,
                        editedAt: Number(params.time)
                    });
                }
                return r;
            });
            handle.helphubRequests.sort(function (a, b) { return b.rawTime - a.rawTime; });
            handle.renderRequestsList();
            handle.attachListEventListeners();
        }
        applyEditLocally();

       
        handle.fanoutToBroadcastSiblings(requestId, params);
    }

    updateUserFollowup(requestId, newText, prevServerTs, overrideNowTs) {
        var handle = this;
        var existingReq = (handle.helphubRequests || []).find(function (r) {
            return String(r.id) === String(requestId);
        });
        var preservedType = (existingReq && existingReq.contentType)
            ? (existingReq.contentType.toLowerCase().replace(/ /g, "") === "customwebbanner"
                ? "BANNER"
                : existingReq.contentType.toUpperCase().replace(/ /g, ""))
            : "BANNER";
        var prevFollowupTime = Number(prevServerTs) || 0;
        if (!prevFollowupTime && existingReq && Array.isArray(existingReq.reopenEntries) && existingReq.reopenEntries.length) {
            prevFollowupTime = Number(
                existingReq.reopenEntries[existingReq.reopenEntries.length - 1].rawTime
            ) || 0;
        }
        var nowTs = Number(overrideNowTs) || Date.now();
        var params = {
            action: "updateUserRequestDetails",
            reqId: String(requestId),
            actionStatus: "REOPEN",
            description: newText,
            materialId: "0",
            materialType: preservedType,
            time: String(nowTs),
            orgid: this.orgid,
            Scope: this.scope
        };

        function applyEditLocally() {
            handle.helphubRequests = handle.helphubRequests.map(function (r) {
                if (String(r.id) !== String(requestId)) return r;
                var reopens = Array.isArray(r.reopenEntries) ? r.reopenEntries.slice() : [];
                if (reopens.length) {
                    var last = Object.assign({}, reopens[reopens.length - 1], {
                        rawDescription: newText,
                        rawTime: nowTs,
                        date: handle.formatRequestTime(nowTs),
                        edited: true,
                        editedAt: nowTs
                    });
                    reopens[reopens.length - 1] = last;
                }
                return Object.assign({}, r, {
                    reopenEntries: reopens,
                    rawTime: nowTs,
                    date: handle.formatRequestTime(nowTs)
                });
            });
            handle.helphubRequests.sort(function (a, b) {
                return (b.rawTime || 0) - (a.rawTime || 0);
            });
            try {
                var prevCache = handle.readRequestCache();
                var prevEntry = prevCache[String(requestId)] || {};
                var prevDropped = Array.isArray(prevEntry.droppedFollowupTimes)
                    ? prevEntry.droppedFollowupTimes.slice() : [];
                if (prevFollowupTime && prevDropped.indexOf(prevFollowupTime) === -1) {
                    prevDropped.push(prevFollowupTime);
                }
                handle.cacheRequestForAllSiblings(requestId, {
                    lastFollowupEdited: {
                        prevRawTime: prevFollowupTime,
                        newRawTime: nowTs,
                        text: newText,
                        editedAt: nowTs
                    },
                    droppedFollowupTimes: prevDropped
                });
            } catch (e) { }
            handle.renderRequestsList();
            handle.attachListEventListeners();
        }

        handle.applySubProductScope(params);
       
        applyEditLocally();
        handle.fanoutToBroadcastSiblings(requestId, params);
    }
}

RequestContentWrapper.instance = null;//$Id$ 
class ScreenRecording {
    static instance = null;

    constructor(stopRecordingCallback) {
        if (ScreenRecording.instance) {
            return ScreenRecording.instance;
        }
        ScreenRecording.instance = this;

        this.mediaRecorder = '';
        this.recordedData = [];
        this.screenStream = null;
        this.audioStream = null;
        this.stopRecordingCallback = stopRecordingCallback;

    }

    async startRecording(callback) {
        try {

            this.screenStream = await navigator.mediaDevices.getDisplayMedia({
                video: true,
                preferCurrentTab: true
            });

            this.audioStream = await navigator.mediaDevices.getUserMedia({
                audio: true
            });

            const combinedStream = new MediaStream([
                ...this.screenStream.getTracks(),
                ...this.audioStream.getAudioTracks()
            ]);

            this.mediaRecorder = new MediaRecorder(combinedStream, {
                mimeType: "video/webm; codecs=vp9,opus"
            });

            this.mediaRecorder.ondataavailable = event => {
                if (event.data.size > 0) {
                    this.recordedData.push(event.data);
                }
            };

            this.mediaRecorder.onstop = () => {
                this.confirmation();
            };

            this.screenStream.getVideoTracks()[0].addEventListener("ended", () => {
                this.mediaRecorder.stop();
            });
            callback("success");
            this.mediaRecorder.start();
        }
        catch (error) {
            callback("error");
        }
    }

    stopRecording() {
        try {
            [...this.screenStream.getTracks(), ...this.audioStream.getTracks()].forEach(track => track.stop());
        } catch (error) {
            alert(error.message);
        }
    }
    confirmation() {
        var status = window.confirm('Video has been successfully recorded. Would you like to download this video?');
        if (status === true) {
            this.downloadVideo();
        } else {
            var msg = {
                status: "failed",
                errorText: "Video is not downloaded"
            }
            this.stopRecordingCallback(msg);
        }
    }

    downloadVideo() {
        const blob = new Blob(this.recordedData, { type: "video/webm" });
        const url = URL.createObjectURL(blob);

        const a = document.createElement("a");
        a.href = url;
        a.download = "recorded-video.webm";
        document.body.appendChild(a);
        a.click();

        URL.revokeObjectURL(url);
        document.body.removeChild(a)
        alert('The video has been successfully downloaded');
        this.stopRecordingCallback();
    }
}


//$Id$
class WalkthroughTextGenerator {
    static instance = '';
    constructor() {
        this.data = {}
    }
    getTitle() {
        return WalkthroughVerification.getInstance().walkthroughSDK.data.name;

    }
    getDefaultText() {
        var walkthroughRef = WalkthroughVerification.getInstance().walkthroughSDK;
        var stepCompletion = walkthroughRef.data.stepCompletionConfig;
        if (stepCompletion[walkthroughRef.ongoingStepNumber] == 'Allow Interaction') {
            return 'Fill the Field';
        }
        else if (stepCompletion[walkthroughRef.ongoingStepNumber] == 'TargetElement') {
            return walkthroughRef.ongoingStepElement.innerText ? 'Click "' + walkthroughRef.ongoingStepElement.innerText + '"' : 'Click here'
        }
        else {
            return this.readTextFromTooltip(walkthroughRef);
        }
    }
    readTextFromTooltip(walkthroughRef) {
        var textelements = walkthroughRef.WalkthroughLayoutManager.ongoingStepLayout.querySelectorAll('[id^="layoutContainer"] > #tooltipLayout > #frame-parent-container > #row-container > .row-child > #textbuilder');
        var res = '';
        textelements.forEach(element => {
            res += element.innerText.trim() ? element.innerText + '\n' : '';
        })
        return res ? res : 'Step ' + (walkthroughRef.ongoingStepNumber + 1);
    }
    static getInstance() {
        if (!WalkthroughTextGenerator.instance) {
            WalkthroughTextGenerator.instance = new WalkthroughTextGenerator();
        }
        return WalkthroughTextGenerator.instance;
    }
}//$Id$
class HTMLGeneration {
    static instance = '';
    constructor() {
        this.type = "";
        this.ExtensionId = "pdpmpoaehnemjojblnnldhhhgnlglhnb";
        this.resJSON = {
            header: {
                favIconLink: '',
                title: '',
                steps: 0
            },
            content: []
        }
        this.textFor = {
            "walkthrough": WalkthroughTextGenerator,
        }
    }
    getOutputData() {
        this.resJSON.header.steps = this.resJSON.content.length;
        return this.resJSON;
    }
    addScreenshot(type, index) {
        this.type = type;
        if (!this.resJSON.header.favIconLink) {
            this.setHeader();
            this.setTabIcon();
        }
        try {
            var res = { imgLink: '', text: '' };
            res["text"] = this.textFor[this.type].getInstance().getDefaultText();

            let request = {
                action: "screenShot",
                data: this.micsWalkthroughConfig,
                index: index - 1
            }
            ExtensionCommunicator.sendMessageToExtension(request, (response) => {
                res["imgLink"] = response.imgURl;
                response.index ? this.resJSON.content[response.index] = res : this.resJSON.content.push(res);// for firefox indexed approach needs to be done
            })
        } catch (err) {

        }
    }
    setHeader() {
        var title = this.textFor[this.type].getInstance().getTitle();
        this.resJSON.header.title = title;
    }
    setTabIcon() {
        var handle = this;
        ExtensionCommunicator.sendMessageToExtension({ action: "getIcon" }, (response) => {
            handle.faviconToBase64(response.imgURl ? response.imgURl : response).then(base64 => {
                if (base64) {
                    handle.resJSON.header.favIconLink = base64
                }
                else {
                    handle.resJSON.header.favIconLink = '';
                }
            })
        }
        )
    }
    async faviconToBase64(faviconUrl) {
        try {
            const response = await fetch(faviconUrl);
            if (!response.ok) {
                throw new Error(`Failed to fetch favicon: ${response.statusText}`);
            }
            const blob = await response.blob();
            return await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onloadend = () => resolve(reader.result);
                reader.onerror = reject;
                reader.readAsDataURL(blob);
            });
        } catch (error) {
            console.error('Error:', error);
            return null;
        }
    }
    static getInstance() {
        if (!HTMLGeneration.instance) {
            HTMLGeneration.instance = new HTMLGeneration();
        }
        return HTMLGeneration.instance;
    }
}//$Id$
class InproductMsgListener {
    static listener = null;
    constructor(inproductConf , orgid) {
        this.inproductConf = inproductConf;
        this.orgid = orgid;
        this.inproducttypevslistenerinstance = {
            "walkthrough": {
                "verify": WalkthroughVerification,
                "preview": WalkthroughPreview,
                "Automate": AutomatedWalkthrough,
                "video": WalkthroughVideoRecord,
                "smarttour": WalkthroughSmartTour,
                "create": WalkthroughBuilderSDK,
                "edit": WalkthroughBuilderSDK,
                "downloadashtml": WalkthroughVerification
            },
            "selfhelp":{
                "verify":SelfhelpVerification,
                "viewinproduct":SelfhelpPreview,
            },
            "checklist":{
                "verify":SelfhelpVerification,
                "viewinproduct":SelfhelpPreview,
            }
        };
        this.trustedsubdomains = ["zoho", "localzoho", "manageengine", "localmanageengine", "zohocloud", "zohonoc"];
        this.setListenerForStartTour();
        this.seteventlistener();
        this.notifyReferrer();
    }
    static initialiseListener(inproductConf,orgid) {
        if (InproductMsgListener.listener === null) {
            InproductMsgListener.listener = new InproductMsgListener(inproductConf,orgid);
        }
        return;
    }
    
    seteventlistener() {
        var handle = this;
        window.addEventListener("message", function (payload) {
            if (payload.data.source === "micsinproduct" && payload.data.startProcess) {
                if (!Inproductutility.validatePostMessageOrigin(payload, "openerDomain")) return;
                var inproducttype = payload.data.type.toLowerCase();
                var action = payload.data.message.action;
                var instance;
                try {
                 instance = handle.inproducttypevslistenerinstance[inproducttype][action].getInstance();
                 if ((inproducttype === 'selfhelp' || inproducttype === 'checklist') && payload.data.message) {
                    payload.data.message.type = inproducttype;
                 }
                 instance.processMessage(payload.data.message);
                } catch (error) {
                }
                
                
            }
        });
    }

    notifyReferrer() {
        if (window.opener != null && Inproductutility.validatePostMessageOrigin({origin: document.referrer}, "openerDomain") ) {
            window.opener.postMessage(
                { source: "micsinproductsdk", action: 'readyToStart' }, document.referrer);
        }
    }

    closeConnection() {
        if ( window.opener != null && Inproductutility.validatePostMessageOrigin({origin: document.referrer}, "openerDomain")) {
            window.opener.postMessage(
                { source: "micsinproductsdk", action: 'closeConnection' }, document.referrer);
        }
    }

    static getTopLevelDomain(origin) {
        try {
            const hostname = new URL(origin).hostname;
            // Split by dot and take last 2 parts → "zoho.com", "zohotest.com" etc 
            const parts = hostname.split(".");
            return parts.slice(-2).join(".");
        } catch (e) {
            return null;
        }
    }

    setListenerForStartTour() {
        if (!window.opener) return;
        window.opener.postMessage({ targetname: "walkthroughsdk", status: "readyToStartTour" }, "*");
        window.addEventListener("message", function (event) {
            if (event.data.targetname === "micsinproduct" && event.data.action == "startTour") {
                let senderdomain = InproductMsgListener.getTopLevelDomain(event.origin);
                let recieverdomain = InproductMsgListener.getTopLevelDomain(window.location.origin);
                // check senderdomain and recieverdomain
                if(senderdomain==recieverdomain){
                    WalkthroughSmartTour.getInstance().processMessage(event.data.message,event);
                }
                else{
                    console.warn("DAP SDK - domain mismatch in smarttour:", senderdomain, "vs", recieverdomain);
                }
            }
        });
    }

}

class InproductCompletionListener {
    static sendStatus(inproducType, msg) {
        if (!window.opener) return;
        window.opener.postMessage({ action: "completed", inproducttype: inproducType, "source": "micsinproductsdk", "message": msg }, document.referrer);
    }
    static sendMsg(action,inproducttype,msg){
        if (!window.opener) return;
        window.opener.postMessage({action:action,inproducttype:inproducttype,message:msg, source: "micsinproductsdk"},document.referrer);
    }
}
/*$Id$*/
class MicsTextToSpeech {
    static instance = null;
    constructor() {
        this.speechSynthesis = window.speechSynthesis;
        this.utterance = new SpeechSynthesisUtterance();
        this.utteranceOptions = {
            voice: "english-us espeak",
            lang: "en-US",
            pitch: .75,
            rate: 1
        };
        if (this.utteranceOptions) {
            if (this.utteranceOptions.voice) {
                this.speechSynthesis.onvoiceschanged = e => {
                    const voice = this.speechSynthesis.getVoices().find(({
                        name: _name
                    }) => _name === this.utteranceOptions.voice);
                    this.utterance.voice = voice;
                }
                this.speechSynthesis.getVoices();
            }
            let { lang, rate, pitch } = this.utteranceOptions;
            Object.assign(this.utterance, {
                lang, rate, pitch
            });
        }
    }
    startTTS(text, callback) {
        this.utterance.text = text;
        this.utterance.onstart = () => {
        };

        this.utterance.onend = () => {
            if (callback) callback();
        };

        this.speechSynthesis.speak(this.utterance);
    }
    static getInstance() {
        if (!MicsTextToSpeech.instance) {
            MicsTextToSpeech.instance = new MicsTextToSpeech();
        }
        return MicsTextToSpeech.instance;
    }
}//$Id$
class AutomatedWalkthrough {
    static instance = "";
    constructor() {
        this.data = "";
        this.walkthroughSDK = ""
        this.overWriteFunc = { "sendMetric": { "rendered": this.tooltipRendered.bind(this), "endTour": this.tourEnded.bind(this), "error": this.handleError.bind(this), "completed": this.tooltipCompleted.bind(this), "quitted": this.tooltipQuitted.bind(this) } };
        this.targetElement = "";
        this.enableTTS = "";
        this.cursorInstance = "";
        this.showTooltipTimer = null;
        this.animationTimer = null;
        this.parentCallBacks = {};
    }
    processMessage(data, enableTTS, parentCallBacks) {
        this.data = data;
        this.enableTTS = enableTTS;
        this.walkthroughSDK = new WalkthroughWrapper();
        this.walkthroughSDK.init(this.data, this.overWriteFunc);
        this.walkthroughSDK.start(this.data);
        this.parentCallBacks = parentCallBacks || {};
        this.insertCursor();
    }
    insertCursor() {
        var shadowRootRef = document.querySelector('walkthrough-builder').shadowRoot;
        var cursorDiv = document.createElement('div');
        cursorDiv.setAttribute("id", "micscursor");
        cursorDiv.style = "position: absolute; top: 0; left: 0; font-size: 1.8vw; z-index:111111111111111; visibility:hidden;";
        cursorDiv.innerHTML = `<svg  height="24px" viewBox="0 -960 960 960" width="27px" fill="#d4610c"><path d="M419-80q-28 0-52.5-12T325-126L107-403l19-20q20-21 48-25t52 11l74 45v-328q0-17 11.5-28.5T340-760q17 0 29 11.5t12 28.5v200h299q50 0 85 35t35 85v160q0 66-47 113T640-80H419ZM240-720v173q-45-26-72.5-71.5T140-720q0-83 58.5-141.5T340-920q83 0 141.5 58.5T540-720q0 56-27 101.5T441-547v-173q0-42-30-71t-71-29q-42 0-71 29t-29 71Z"/></svg>`;
        shadowRootRef.appendChild(cursorDiv);
    }
    tooltipRendered(data) {
        this.cursorInstance = Cursor.getInstance();
        this.setTargetElementForTrigger();
        this.cursorInstance.initialize(this.targetElement);
        var toottipText = this.readTextFromTooltip();

        if (this.enableTTS && this.data.stepCompletionConfig[this.walkthroughSDK.ongoingStepNumber] == "Allow Interaction") {
            MicsTextToSpeech.getInstance().startTTS(toottipText, null);
        }
        else if (this.enableTTS) {
            MicsTextToSpeech.getInstance().startTTS(toottipText, this.startAnimation.bind(this))
        }
        else if (this.data.stepCompletionConfig[this.walkthroughSDK.ongoingStepNumber] != "Allow Interaction") {
            this.startAnimation(this);
        }
    }
    startAnimation() {
        var self = this;
        this.showTooltipTimer = setTimeout(() => {
            self.cursorInstance.startAnimation();
            self.animationTimer = setTimeout(() => {
                self.triggerEvents();
            }, 1000);
        }, 3000);
    }
    tooltipCompleted(data) {
        clearTimeout(this.showTooltipTimer);
        clearTimeout(this.animationTimer);
        this.cursorInstance.hideCursor();
    }
    handleError(data) {
        clearTimeout(this.showTooltipTimer);
        clearTimeout(this.animationTimer);
        var message = {
            status: "failed",
            data: data
        }
        this.parentCallBacks.error ? this.parentCallBacks.error(data) : InproductCompletionListener.sendStatus("walkthrough", message);

    }
    tooltipQuitted(data) {
        clearTimeout(this.showTooltipTimer);
        clearTimeout(this.animationTimer);
        var message = {
            status: "failed",
        }
        this.parentCallBacks.quitted ? this.parentCallBacks.quitted(data) : InproductCompletionListener.sendStatus("walkthrough", message);
    }
    tourEnded(data) {
        clearTimeout(this.showTooltipTimer);
        clearTimeout(this.animationTimer);
       data.statuscode !=10 ? this.parentCallBacks.endTour ? this.parentCallBacks.endTour(data) : this.showCompletionPopup() : null;
    }
    showCompletionPopup() {
        var message = {
            status: "success",
        }
        document.body.insertAdjacentHTML('beforeend', '<div id="micsEAutomatedWalkthrough" style="position: absolute; width: 100%; height: 100%; top: 0px; left: 0px; background-color: rgba(0, 0, 0, 0.25); backdrop-filter: blur(3px); z-index: 2147483647;"><div id="completion_popup" style="position: absolute; left: calc(50% - 11.5vw); top: 30%; width: 21vw; height: max-content; padding: 1.8vw 2vw; border-radius: .3vw; background: #fff; box-shadow: rgba(17, 17, 26, 0.1) 0px 0px 16px;z-index:11111111111111111111;"> <div id="top" style="display: flex;align-items: center;justify-content: center;"> <div id="icon_parent" style=" height: 4vw; width: 4vw; background: #dbffea85; display: flex; justify-content: center; align-items: center; border-radius: 50%; "> <svg height="35px" viewBox="0 -960 960 960" width="35px" fill="#008100"><path d="M382-240 154-468l57-57 171 171 367-367 57 57-424 424Z"></path></svg> </div> </div> <div id="text" style=" margin-top: 1.3vw; display: flex; align-items: center; justify-content: center; flex-direction: column; font-weight: 500; font-size: .85vw; opacity: .75; "> <span style=" font-size: 1vw; font-weight: 600; opacity: .75; ">Tour Completed!</span>  </div> <div id="footer" style=" margin-top: 1.2vw; display: flex; align-items: center; justify-content: center; "> <div id="button" style=" padding: .5vw 1.3vw; background: #f56e6e; color: #fff; border-radius: .15vw; cursor: pointer; ">Close</div> </div> </div></div>')
        document.querySelector('#micsEAutomatedWalkthrough >#completion_popup >#footer > #button').addEventListener("click", () => {
            InproductCompletionListener.sendStatus("walkthrough", message);
        })
    }
    readTextFromTooltip() {
        const previewContentDivs = document.querySelector('walkthrough-builder').shadowRoot.querySelectorAll('#previewcontentdiv');
        let combinedText = '';
        previewContentDivs.forEach(div => {
            combinedText += div.textContent.trim() + ' ';
        });
        combinedText = combinedText.trim();
        return combinedText;
    }
    setTargetElementForTrigger() {
        var stepCompletionType = this.data.stepCompletionConfig[this.walkthroughSDK.ongoingStepNumber]
        if (stepCompletionType == "TargetElement") {
            if (this.walkthroughSDK.WalkthroughLayoutManager.ongoingStepLayout.querySelector(`[id^="layoutContainer"][trigger_targetelement="true"]`)) {
                this.targetElement = this.walkthroughSDK.WalkthroughLayoutManager.ongoingStepLayout.querySelector(`[id^="layoutContainer"] #footer-container #row-container .row-child > #buttonbuilder > #buttoncontainer[goto_action="NextStep"] > #buttonElement`);
            }
            else {
                this.targetElement = this.walkthroughSDK.ongoingStepElement;
            }
        }
        else if (stepCompletionType == "Block Element") {
            this.targetElement = this.walkthroughSDK.WalkthroughLayoutManager.ongoingStepLayout.querySelector(`[id^="layoutContainer"] #footer-container #row-container .row-child > #buttonbuilder > #buttoncontainer[goto_action="NextStep"] > #buttonElement`);
        }
        else {
            this.targetElement = this.walkthroughSDK.WalkthroughLayoutManager.ongoingStepLayout.querySelector(`[id^="layoutContainer"] #footer-container #row-container .row-child > #buttonbuilder > #buttoncontainer[goto_action="NextStep"] > #buttonElement`);
        }
    }
    triggerEvents() {
        this.targetElement.dispatchEvent(this.createEvent("click"));
        this.targetElement.dispatchEvent(this.createEvent("mousedown"));
    }
    createEvent(eventname) {
        return new MouseEvent(eventname, {
            bubbles: true,
            cancelable: true,
            view: window
        });
    }
    static getInstance() {
        if (!AutomatedWalkthrough.instance) {
            AutomatedWalkthrough.instance = new AutomatedWalkthrough();
        }
        return AutomatedWalkthrough.instance;
    }
}


class Cursor {
    static instance = null;
    constructor() {
        this.cursorRef = document.querySelector('walkthrough-builder').shadowRoot.querySelector("#micscursor");
        this.targetElement = "";
        this.x = "";
        this.y = "";
        this.addEventListeners();
    }
    initialize(targetElement) {
        this.targetElement = targetElement;
        this.setTransitionPoint();

    }
    setTargetPos() {
        const triggerElementPos = this.getElementPosition(this.targetElement);
        const xPos = window.scrollX + triggerElementPos.left + triggerElementPos.width / 2;
        const yPos = window.scrollY + triggerElementPos.top + triggerElementPos.height / 2;
        const cursorElementPos = this.getElementPosition(this.cursorRef);
        this.cursorRef.style.setProperty("--endX", this.x);
        this.cursorRef.style.setProperty("--endY", this.y);
        this.x = xPos - cursorElementPos.width / 2 + 'px';
        this.y = yPos - cursorElementPos.height / 2 + 'px';
    }
    setTransitionPoint() {
        this.setTargetPos();
        this.cursorRef.style.animation = "none";
        this.cursorRef.style.setProperty("--endX", this.x);
        this.cursorRef.style.setProperty("--endY", this.y);
    }
    startAnimation() {
        this.cursorRef.style.animation = 'moveAndScale 1s ease-in-out forwards';
        this.showCursor();

    }
    hideCursor() {
        this.cursorRef.style.setProperty("--startX", this.x);
        this.cursorRef.style.setProperty("--startY", this.y);
        this.cursorRef.style.visibility = "hidden";
        this.removeEventListeners();
    }
    showCursor() {
        this.cursorRef.style.visibility = "visible";
    }
    getElementPosition(element) {
        return element.getBoundingClientRect();
    }
    addEventListeners() {
        var handle = this;
        window.addEventListener('resize', (e) => { handle.handleResize() });
    }
    handleResize() {
        var self = this;
        setTimeout(() => {
            self.setTransitionPoint(self.targetElement);
        }, 200)
    }
    removeEventListeners() {
        window.removeEventListener("resize", this.handleResize());
    }

    static getInstance() {
        if (!Cursor.instance) {
            Cursor.instance = new Cursor();
        }
        return Cursor.instance;
    }
}//$Id$
class WalkthroughWrapper extends WalkthroughSDK {
    constructor() {
        super(InproductMsgListener.listener.inproductConf, InproductMsgListener.listener.orgid, {});
        this.data = [];
        this.metricsMapping = [
            "rendered",
            "completed",
            "quitted",
        ]
        this.lastTooltipIndex = -1;
        this.overWriteFunc = {};
    }
    init(data, overWriteFunc) {
        this.data = data;
        this.overWriteFunc = overWriteFunc || {};
        this.setValidationConf();
    }
    setValidationConf(){
        var workspaceConf = this.data.workspaceConf;
        var productname = "";
        if(workspaceConf){
            this.setworkspaceconf(workspaceConf);
            productname = workspaceConf.activeWorkspace?.product_name;
        }
        if(workspaceConf && workspaceConf.walkthroughConf && workspaceConf.walkthroughConf[productname] && workspaceConf.walkthroughConf[productname].urlValidationConf){
            var urlvalidationconf = JSON.parse(workspaceConf.walkthroughConf[productname].urlValidationConf);
            this.urlUtil.setUrlValidationConf(urlvalidationconf);
        }
    }

    start() {
        this.setverifydata(this.data);
        
        this.overWriteFunc["datadelivered"] ? this.overWriteFunc["datadelivered"]({status: "datadelivered"}) : "";
    }
    sendMetric(data) {
        let metric = {
            'action': "metrics",
            'walkthroughid': this.flowID,
            'promotionid': this.promotionId,
            'orgid': this.orgid,
            'sessionstarttime': this.sessionStartTime,
            'stepnumber': this.ongoingStepNumber + 1,
            'statuscode': data.statusCode,
            'errorcode': data.errorCode ? data.errorCode : undefined,
            'serviceid': this.serviceid,
            'Scope': this.datamanager.WalkthroughData[this.flowID].scope,
            'flowID': this.flowID
        }
        var featureCallBack = this.overWriteFunc["sendMetric"];
        this.lastTooltipIndex = this.lastTooltipIndex < this.ongoingStepNumber ? this.ongoingStepNumber : this.lastTooltipIndex;
        if(featureCallBack){
            if (this.ongoingWalkthroughData.templates.length - 1 == this.ongoingStepNumber && (data.statusCode == 2 || data.statusCode == 3 || data.statusCode == 10)) {
                metric.status = "success";
                featureCallBack["endTour"] ? featureCallBack["endTour"](metric) : "";
            }
            else if (data.statusCode <= 3) {
                data.statusCode == 3 ? metric["status"] = "failed" : "",
                    featureCallBack[this.metricsMapping[data.statusCode - 1]] ? featureCallBack[this.metricsMapping[data.statusCode - 1]](metric) : "";
            }
            else {
                metric.status = "failed";
                featureCallBack["error"] ? featureCallBack["error"](metric) : "";
            }
        }
        
    }
    checkTooltipAlreadyRendered() {
        return this.lastTooltipIndex < this.ongoingStepNumber;
    }
}
//$Id$
class WalkthroughPreview {
    static instance = "";
    constructor() {
        this.overWriteFunc = { "sendMetric": { "endTour": this.tourEnded.bind(this), "error": this.handleError.bind(this) } };
    }
    processMessage(data) {
        this.data = data;
        this.walkthroughSDK = new WalkthroughWrapper();
        this.walkthroughSDK.init(this.data, this.overWriteFunc);
        this.walkthroughSDK.start(this.data);
    }
    handleError(data) {
        var message = {
            status: "failed",
            data: data
        }
        InproductCompletionListener.sendStatus("walkthrough", message);
    }
    tourEnded(data) {
        var message = {
            status: "success",
        }
        InproductCompletionListener.sendStatus("walkthrough", message);
    }
    static getInstance() {
        if (!WalkthroughPreview.instance) {
            WalkthroughPreview.instance = new WalkthroughPreview();
        }
        return WalkthroughPreview.instance;
    }
}//$Id$
class WalkthroughVerification {
    static instance = '';
    constructor() {
        this.additionalAction = {
            "htmlgeneration": HTMLGeneration
        }
        this.walkthroughSDK = "";
        this.tabChanged = false;
        this.screenShotTaken = false;
        this.overWriteFunc = { "sendMetric": { "rendered": this.tooltipRendered.bind(this), "endTour": this.tourEnded.bind(this), "error": this.handleError.bind(this) , "quitted":this.handleQuit.bind(this)},"datadelivered":this.dataDeliveried.bind(this) };
    }
    processMessage(data) {
        this.data = data;
        // this.addEventlListeners();
        this.walkthroughSDK =this.walkthroughSDK?this.walkthroughSDK:new WalkthroughWrapper();
        this.walkthroughSDK.init(this.data, this.overWriteFunc);
        this.walkthroughSDK.setworkspaceconf(data.workspaceConf);  
        this.walkthroughSDK.start(this.data);
    }
    tooltipRendered(metrics) {
        var self = this;
        InproductCompletionListener.sendMsg('metrics','walkthrough',metrics);
        // this.screenShotTaken = false;
        // if (self.canTakeScreenShot() && !this.walkthroughSDK.checkTooltipAlreadyRendered()) {
        //     setTimeout(() => { // after rendering tooltip it takes few seconds for show 
        //         if (!self.tabChanged && !self.screenShotTaken) {
        //             self.screenShotTaken = true;
        //           //  HTMLGeneration.getInstance().addScreenshot("walkthrough", metrics.stepnumber);
        //         }
        //     }, 200);
        // }
    }
    handleError(data) {
        var message = {
            status: "failed",
            data: data
        }
        // this.removeEventListeners();
        InproductCompletionListener.sendStatus("walkthrough", message);
    }
    handleQuit(data){
        var message = {
            status: "quitted",
            data: data
        };
        InproductCompletionListener.sendStatus("walkthrough", message);
    }
    tourEnded() {
        var message = {
            status: "success",
            data: {}
        };
        // (this.canTakeScreenShot()) ? message.data["htmlGeneration"] = HTMLGeneration.getInstance().getOutputData() : "";
        // this.removeEventListeners();
        InproductCompletionListener.sendStatus("walkthrough", message);
    }
    dataDeliveried(data){
        InproductCompletionListener.sendMsg('datadelivered','walkthrough',data);
    }
    // addEventlListeners() {
    //     var handle = this;
    //     document.addEventListener("visibilitychange", (e) => { handle.handleTabChanged() });
    // }
    // removeEventListeners() {
    //     document.removeEventListener("visibilitychange", this.handleTabChanged());
    // }
    // handleTabChanged() {
    //     var self = this;
    //     if (self.canTakeScreenShot() && document.hidden) {
    //         self.tabChanged = true;
    //     } else {
    //         if (self.canTakeScreenShot() && !self.screenShotTaken && !self.walkthroughSDK.checkTooltipAlreadyRendered()) {
    //             setTimeout(() => {
    //                 self.screenShotTaken = true;
    //                // HTMLGeneration.getInstance().addScreenshot("walkthrough");
    //             }, 200);
    //         }
    //         self.tabChanged = false;
    //     }
    // }

    canTakeScreenShot() {
        return this.data.extensionConf && !(this.data.extensionConf.status == "noextension" || this.data.extensionConf.status == "oldextension");
    }

    static getInstance() {
        if (!WalkthroughVerification.instance) {
            WalkthroughVerification.instance = new WalkthroughVerification();
        }
        return WalkthroughVerification.instance;
    }
}//$Id$
class WalkthroughVideoRecord {
    static instance = null;
    constructor(data) {
        this.data = data;
        this.statusMsg = {
            status: "failed"
        }
        this.ScreenRecordingSDK = new ScreenRecording(this.sendCompletionStatus.bind(this));
        this.callBacks = { "endTour": this.stopRecording.bind(this), "quitted": this.stopRecording.bind(this), "error": this.stopRecording.bind(this) };
    }
    processMessage(data) {
        this.data = data;
        this.ScreenRecordingSDK.startRecording(this.handleRecordingPermission.bind(this));
    }
    handleRecordingPermission(status) {
        if (status == "success") {
            this.walkthroughSDK = new AutomatedWalkthrough();
            this.walkthroughSDK.processMessage(this.data, true, this.callBacks);
        }
        else {
            var msg = {
                "status": "failed",
            }
            InproductCompletionListener.sendStatus("walkthrough", msg)
        }
    }
    stopRecording(data) {
        this.statusMsg = data;
        if (data.status == "failed") {
            this.sendCompletionStatus(data)
        }
        else {
            this.ScreenRecordingSDK.stopRecording(data);
        }
    }
    sendCompletionStatus(msg) {
        InproductCompletionListener.sendStatus("walkthrough", msg || this.statusMsg);

    }
    static getInstance() {
        if (!WalkthroughVideoRecord.instance) {
            WalkthroughVideoRecord.instance = new WalkthroughVideoRecord();
        }
        return WalkthroughVideoRecord.instance;
    }
}//$Id$
class WalkthroughSmartTour {
    static instance = "";
    constructor() {
        this.data = "";
    }
    processMessage(data) {
        if (WalkthroughSDK.instance) {
            var sdkinstance = WalkthroughSDK.instance;
            if(data.hasDynamicConf){
                sdkinstance.setDynamicConf(data.walkthroughconf);
                data.workspaceConf ? sdkinstance.setworkspaceconf(data.workspaceConf):"";
            }
            if (sessionStorage.getItem("currentongoingWalkthroughDataGID")) return;
            sdkinstance.startsmarttour(data);
            return;
        }
        sessionStorage.setItem("walkthroughsdkdata", JSON.stringify(data));
    }
    static getInstance() {
        if (!WalkthroughSmartTour.instance) {
            WalkthroughSmartTour.instance = new WalkthroughSmartTour();
        }
        return WalkthroughSmartTour.instance;
    }
}
/*$Id$*/
class SelfhelpPreview{
    static instance = '';
    static instance = '';
    constructor() {
        this.selfhelpSDK = "";
        this.overWriteFunc = { "datadelivered":this.dataDeliveried.bind(this) , "triggered": this.materialTriggered.bind(this) };
    }
    processMessage(data) {
        this.data = data;
        this.selfhelpSDK = new SelfhelpWrapper();
        this.selfhelpSDK.init(this.data, this.overWriteFunc);
        this.selfhelpSDK.setworkspaceconf(data.workspaceConf);  
        this.selfhelpSDK.start(this.data);
    }
    handleError(data) {
        var message = {
            status: "failed",
            data: data
        }
        InproductCompletionListener.sendStatus("walkthrough", message);
    }
    materialTriggered(){

    }   
    dataDeliveried(data){
        InproductCompletionListener.sendMsg('datadelivered','walkthrough',data);
    }

    static getInstance() {
        if (!SelfhelpVerification.instance) {
            SelfhelpVerification.instance = new SelfhelpVerification();
        }
        return SelfhelpVerification.instance;
    }
}/*$Id$*/
class SelfhelpVerification{
    static instance = '';
    constructor() {
        this.selfhelpSDK = "";
        this.overWriteFunc = { 
            "selfhelp":{
                "delivered":this.dataDeliveried.bind(this),
                "materialClicked":this.materialTriggered.bind(this),
            }
        }
    }
    processMessage(data) {
        this.data = data;
        this.inproducttype = data.type ? data.type.toLowerCase() : "selfhelp";
        this.selfhelpSDK = new SelfhelpWrapper(data.inproductConf,data.orgid);
        this.selfhelpSDK.init(this.data, this.overWriteFunc);
        this.selfhelpSDK.showSelfhelp();
    }

    handleError(data) {
        var message = {
            status: "failed",
            data: data
        }
        InproductCompletionListener.sendStatus(this.inproducttype, message);
    }
    materialTriggered(data){
        InproductCompletionListener.sendMsg('materialTriggered',this.inproducttype,data);
    }   
    dataDeliveried(data){
        InproductCompletionListener.sendMsg('datadelivered',this.inproducttype,data);
    }


    static getInstance() {
        if (!SelfhelpVerification.instance) {
            SelfhelpVerification.instance = new SelfhelpVerification();
        }
        return SelfhelpVerification.instance;
    }
}/*$Id$*/
class SelfhelpWrapper extends selfhelpsdk{
    constructor(){
        super(InproductMsgListener.listener.inproductConf, InproductMsgListener.listener.orgid);
        this.data = {};
        this.overwriteFunc = {}; 
        this.walkthroughInstance = new WalkthroughWrapper(this.inproductconf,this.orgid);
    }
    init(data , overwriteFunc){
        this.data = data;
        this.overwriteFunc = overwriteFunc; 
        this.domainConf = this.data.videoConf;
        this.domainConf.domainType = Inproductutility.getDomainType(this.data.inproductConf.inproductdomain,location.hostname);
        this.verification = true;
        this.setValidationConf();
    }
    setValidationConf(){
        var workspaceConf = this.data.workspaceconf;
        var productname = "";
        if(workspaceConf){
            this.walkthroughInstance.setworkspaceconf(workspaceConf); 
            productname  = workspaceConf.activeWorkspace.product_name;
        }
        if(workspaceConf && workspaceConf.walkthroughConf && workspaceConf.walkthroughConf[productname] && workspaceConf.walkthroughConf[productname].urlValidationConf){
            var urlvalidationconf = JSON.parse(workspaceConf.walkthroughConf[productname].urlValidationConf);
            this.walkthroughInstance.urlUtil.setUrlValidationConf(urlvalidationconf);
            this.urlUtil.setUrlValidationConf(urlvalidationconf);
        }
    }
    showSelfhelp(){
        this.initialize(this.data);
        this.sendDeleiverStatus();
    }
    loadWalkthroughs(){}
    sendDeleiverStatus(){
        if(this.overwriteFunc["selfhelp"] && this.overwriteFunc["selfhelp"]["delivered"]){
            this.overwriteFunc["selfhelp"]["delivered"]({action : "delivered" , runType:"wrapper"});
        }
    }
    getdatacallback(){
        var renderConf = this.data.renderConf;
        if(renderConf.showAll && renderConf.showGivenContent){
            this.getAllData(this.data.scope);
            this.addNewHelpHub(true);
        }
        else if(renderConf.showAll){
            this.getAllData(this.data.scope);
        }
        else if(renderConf.showGivenContent) {
             this.addNewHelpHub();
                this.data.helphubstyle ? this.updateStyleConfig(this.data.helphubstyle) : ''
        }
    }
    addNewHelpHub(){
        this.nodatahidestatus = this.data.nodatahidestatus;
        // this.selfhelpmateriallist = [...this.selfhelpmateriallist,...this.data.helphubList];
        let dataObj = {};
        let dataList = this.data.helphubList[0];
        dataObj[dataList.url] ? "" : dataObj[dataList.url] = [];
        for (var selfhelpmaterialList of dataList.panellist){
            for(var materialItem of selfhelpmaterialList.materiallist){
                var materialData = {
                    scope: selfhelpmaterialList.Scope,
                    promotionid: selfhelpmaterialList.id,
                    materialid: materialItem.id,
                    materialtype: materialItem.type,
                    displayname: materialItem.displayname,
                    workspaceid: materialItem.workspaceid 
                }
                dataObj[dataList.url].push(materialData);
            }  
        }
        this.dataversion = 2;

        let type = (this.data && (this.data.key || this.data.type)) ? (this.data.key || this.data.type).toLowerCase() : "";
        if (type.includes("checklist")) {
            this.taskdata = {...this.taskdata, ...dataObj};
            this.inserttaskurlsformatch(Object.keys(this.taskdata));
            this.selfhelpcontents.tabswitch.taskdata = true;
            this.selfhelpcontents.tabswitch.helphubdata = true; 
            // this.selfhelpcontents.indicatortext = "Check List";
            // this.selfhelpcontents.popupheader = "Check List";
            this.selectedtab = "taskdata";

            this.calculateTaskBarPercentage();
        } else {

            this.helphubdata = {...this.helphubdata, ...dataObj};
            this.inserturlsformatch(Object.keys(this.helphubdata));
            this.selfhelpcontents.tabswitch.helphubdata = true;
            this.selfhelpcontents.tabswitch.taskdata = true;
            this.selectedtab = this.selectedtab || "helphubdata";
        }
    }
    getAllData(scope){
        var params = {"orgid":handle.orgid, "serviceid":handle.serviceid, "action":"getTip","Scope":scope};
        var handle = this;
        this.micssdktoserverInstance.getMeta(params,"get",
            function orgsuccess(xhttp){
                try{
                    var parsingmeta = JSON.parse(xhttp);
                    handle.nodatahidestatus = parsingmeta.nodatahidestatus;
                    parsingmeta = parsingmeta.hubdata;
                    handle.selfhelpmateriallist = [...handle.selfhelpmateriallist, ...parsingmeta];
                    handle.hideselfhelpforurlchange(handle);
                }
                catch(e){}
            },
            function orgerror(xhttp){ 
                setTimeout(handle.initialize(),30000);
                return false;
            }
        );     
    }
    triggerWalkthrough(ref, materialID ,medium, panelID , scope){ // overwriteFrom SelfHelpSDK
        this.checkForMaterialClickedAction();
        if(this.overwriteFunc["walkthorugh"] && this.overwriteFunc["walkthrough"]["click"]){
            this.overwriteFunc["walkthrough"]["click"]({ action : "click" , runType:"wrapper"});
        }
        this.walkthroughInstance.datamanager.setwalkthroughData(this.data.otherMaterialsData["walkthrough"],scope);
        this.walkthroughInstance.triggerFlow(materialID, "selfhelp", -1, scope); 
    }

    openGuide(selfHelpRef,materialID,workspaceId){
        this.checkForMaterialClickedAction();
        if(this.overwriteFunc["guide"] && this.overwriteFunc["guide"]["click"]){
            this.overwriteFunc["guide"]["click"]({ action : "click" , runType:"wrapper"});
        }
        // this.openGuideInNewtab(selfHelpRef,materialID,workspaceId);
        this.createIframeForGuide(selfHelpRef,materialID,workspaceId);
    }
    openInteractiveVideo(selfHelpRef, materialID,workspaceId,displayname){
        this.checkForMaterialClickedAction();
        if(this.overwriteFunc["interactivevideo"] && this.overwriteFunc["interactivevideo"]["click"]){
            this.overwriteFunc["interactivevideo"]["click"]({ action : "click",runType:"wrapper"});
        }
        this.createIframeForInteractivevideo(selfHelpRef,materialID,workspaceId,displayname);
    }
    openExternalContent(selfHelpRef, materialID,workspaceId,displayname){
        this.checkForMaterialClickedAction();
        if(this.overwriteFunc["externalContent"] && this.overwriteFunc["externalContent"]["click"]){
            this.overwriteFunc["externalContent"]["click"]({ action : "click",runType:"wrapper"});
        }
        this.createIframeForExternalContent(selfHelpRef,materialID,workspaceId,displayname);
    }
    checkForMaterialClickedAction(){
        if(this.overwriteFunc["selfhelp"] && this.overwriteFunc["selfhelp"]["materialClicked"]){
            this.overwriteFunc["selfhelp"]["materialClicked"]({action : "materialClicked" , runType:"wrapper"});
        }
    }
}
/*$Id$*/
class selfhelpUtility{
    constructor(){
        this.allowedTypes = ['div', 'span'];
    }

    createDomElement(doc, data){

        let element = '';

        //create element
        if(this.allowedTypes.includes(data.type)){            
            element = doc.createElement(data.type);
        } 

        //set class
        data.className ? element.className = data.className : "";

        //set id
        data.id ? element.id = data.id : "";

        //set styles
        if(data.styles && Object.keys(data.styles).length > 0){
            for(let key in data.styles){
                element.style[key] = data.styles[key];
            }
        }

        //set attributes
        if(data.attributes && Object.keys(data.attributes).length > 0){
            for(let key in data.attributes){
                element.setAttribute(key, data.attributes[key]);
            }
        }

        //set innerHTML
        data.innerHTML ? element.innerHTML = data.innerHTML : "";
        
        //set innerText
        data.innerText ? element.innerText = data.innerText : "";

        //add children
        if (data.children && data.children.length > 0) {
            data.children.forEach(childData => {
                let child = this.createDomElement(doc, childData);
                element.appendChild(child);
            });
        }

        //set event listeners
        if(data.events && Object.keys(data.events).length > 0){
            for(let key in data.events){
                let eventFn = data.events[key];
                typeof eventFn == "function" ? element.addEventListener(key, data.events[key]) : "";
            }
        }

        return element;
    }

    createFlowlist(doc, materialData, handle){

        let displayData = materialData.displayData;
    
        let flowDivConf = {
            type: 'div',
            className: 'flowlist',
            attributes: {
                'scope': materialData.scope,
                'panelId': materialData.panelId,
                'workspaceId': materialData.workspaceid,
                'materialId': materialData.id,
                'materialType': materialData.type
            },
            children: [
                {
                    type: 'span',
                    className: 'materialicon',
                    innerHTML: displayData.icon
                },
                {
                    type: 'div',
                    id: 'content',
                    children: [
                        {
                            type: 'span',
                            id: 'displayname',
                            innerText: materialData.displayname
                        },
                        {
                            type: 'span',
                            id: 'materialtype',
                            innerText: displayData.displaytype
                        }
                    ]
                }
            ],
            events: {
                "click": callbackfunction
            }
        }

        if (handle.selectedtab === 'taskdata' && materialData.status == "completed") {
            flowDivConf.children.push({
                type: 'span',
                className: 'task-completed-icon',
                attributes: {
                    'style': 'margin-left: auto; display: flex; align-items: center; justify-content: center; color: #02b609; padding: 1px; border-radius: 50%; background-color: #e2fee2;'
                },
                innerHTML: '<svg height="20px" viewBox="0 -960 960 960" width="20px" fill="currentColor"><path d="M382-240 154-468l57-57 171 171 367-367 57 57-424 424Z"></path></svg>'
            });
        }
        var self = this;
        function callbackfunction(event){
            handle.addlistener(materialData, handle);
        }
    
        return this.createDomElement(doc, flowDivConf);
    
    }

    createEmptyStateDiv(doc, styles, innerText){
        let nodataDivConf = {
            type: 'span',
            styles: {
                margin: 'auto',
                textAlign: 'center',
                fontSize: styles.fontSize,
                fontFamily: styles.fontFamily,
                fontWeight: styles.fontWeight,
                color: styles.fontColor
            },
            innerText: innerText
        }
    
        return this.createDomElement(doc, nodataDivConf);
    }

    createLoader(doc){
        let loaderDivConf = {
            type: 'div',
            id: 'loader',
            styles: {
                margin: 'auto'
            },
            children: [
                {
                    type: 'div',
                    id: 'icon'
                }
            ]
        }
        return this.createDomElement(doc, loaderDivConf);
    }

    getSuggestion(instance, params, method, onsuccess, onerror){
        instance.getMeta(params, method, onsuccess, onerror);
    }
}/*$Id$*/
class UrlSegment {
    constructor() {
        this.levels = new Map();
        this.isUrlEnd = false;
        this.fullUrl = null;
    }
}

class UrlMatcher {
    constructor() {
        this.root = new UrlSegment();
    }

    insert(url) {
        const strippedUrl = this.strip(url);
        const splittedUrl = strippedUrl.split('/').filter(Boolean);
        let currentRoot = this.root;
        for (const eachSplit of splittedUrl) {
            if (!currentRoot.levels.has(eachSplit)) {
                currentRoot.levels.set(eachSplit, new UrlSegment());
            }
            currentRoot = currentRoot.levels.get(eachSplit);
        }
        currentRoot.isUrlEnd = true;
        currentRoot.fullUrl = url;
    }

    search(inputUrl, config = { includeSearchParams: false, includeHashValue: false }) {

        let processedInput = inputUrl;
        if (!config.includeHashValue) processedInput = processedInput.split('#')[0];
        if (!config.includeSearchParams) processedInput = processedInput.split('?')[0];

        const stripped = this.strip(processedInput);
        const splittedUrl = stripped.split('/').filter(Boolean);

        const matches = new Set();

        this.searchRecursive(this.root, splittedUrl, 0, matches, config);

        return Array.from(matches);
    }

    searchRecursive(node, segments, index, matches, config) {

        if (index === segments.length) {
            this.collectDescendants(node, matches);
            return;
        }

        const inputSeg = segments[index];

        for (const [patternSeg, childNode] of node.levels) {

            let processedPatternSeg = patternSeg;
            if (!config.includeHashValue) processedPatternSeg = processedPatternSeg.split('#')[0];
            if (!config.includeSearchParams) processedPatternSeg = processedPatternSeg.split('?')[0];

            const isMatch =
                processedPatternSeg === '*' ||
                this.isPlaceholder(processedPatternSeg) ||
                processedPatternSeg === inputSeg;

            if (isMatch) {
                if (childNode.isUrlEnd) {
                    matches.add(childNode.fullUrl);
                }
                this.searchRecursive(childNode, segments, index + 1, matches, config);
            }
        }
    }

    collectDescendants(node, matches) {
        if (node.isUrlEnd) {
            matches.add(node.fullUrl);
        }
        for (const childNode of node.levels.values()) {
            this.collectDescendants(childNode, matches);
        }
    }

    isPlaceholder(segment) {
        return segment.startsWith('{{') && segment.endsWith('}}');
    }

    strip(url) {
        return url.replace(/\/+$/, '').replace(/^\/+/, '');
    }
}

// $Id$

class InProduct_RenderingSDKMessenger {
    static instance;
    constructor() {
        this.targetElement = {
            instance: undefined,
            fullSelector: ''
        };
        this.cqs = new CustomQuerySelector();
    }
    static getInstance() {
        if (!InProduct_RenderingSDKMessenger.instance) {
            InProduct_RenderingSDKMessenger.instance = new InProduct_RenderingSDKMessenger();
        }
        return InProduct_RenderingSDKMessenger.instance;
    }
    processIframeMsg(msgData, source) {
        switch (msgData.action) {
            case "setChildTargetElement":
                this.setTargetElement( msgData, source );
                break;
            case "onParentDomChange":
                this.handleParentDomChange( msgData, source );
                break;
            case "clearChildTarget":
                this.clearTargetElement();
                break;
            case "triggerChildTarget":
                this.triggerTargetElement(msgData, source);
                break;
            case "listenTargetClick":
                this.addTargetClickListener(msgData, source);
                break;
            default:
                break;
        }
    }
    setTargetElement( data ) {
        this.targetElement.instance = new WalkthroughTargetElementHandler(data.payload.childSelector, data.payload.elementMeta);
        this.targetElement.fullSelector = data.payload.fullSelector;
        this.setObserverCallback();
    }
    setObserverCallback() {
        const updateDimensionsToParent = () => {
            let elementData = this.targetElement.instance.getElementData();
            window.parent.postMessage({
                action: "updateTargetData", source:"inproductsdk", origin: "inproduct_childsdk", 
                payload: { fullSelector: this.targetElement.fullSelector, dimensions: elementData.dimensions, isValid: elementData.isValid , isHidden : elementData.isHidden },
                mode: "walkthroughrendering"
            }, "*");
        };
        this.targetElement.instance.onDOMChange(updateDimensionsToParent);
    }
    clearTargetElement() {
        this.targetElement.instance? this.targetElement.instance.clear() : '';
        this.targetElement.instance = undefined;
        this.targetElement.fullSelector = '';
    }
    handleParentDomChange(data) {
        if (this.targetElement.instance && this.targetElement.fullSelector.trim() == data.payload.fullSelector.trim()
            && this.targetElement.instance.isValid) {
            this.targetElement.instance.fetchElementData();
        } else {
            this.setTargetElement(data);
        }
    }
    triggerTargetElement(data) {
        if (this.targetElement.instance && this.targetElement.fullSelector.trim() == data.payload.fullSelector.trim()
            && this.targetElement.instance.isValid) {
            this.targetElement.instance.click();
        } else {
            this.setTargetElement(data);
            this.targetElement.instance.click();
        }
    }
    addTargetClickListener(data) {
        if (this.targetElement.instance && this.targetElement.fullSelector.trim() == data.payload.fullSelector.trim()
            && this.targetElement.instance.isValid) {
            this.targetElement.instance.onClick(() => {
                window.parent.postMessage({
                    action: "elementTriggered", source:"inproductsdk", origin: "inproduct_childsdk", 
                    payload: { fullSelector: this.targetElement.fullSelector },
                    mode: "walkthroughrendering"
                }, "*");
            }, data.payload.eventOptions );
        } else {
            this.setTargetElement(data);
            this.targetElement.instance.onClick(() => {
                window.parent.postMessage({
                    action: "elementTriggered", source:"inproductsdk", origin: "inproduct_childsdk", 
                    payload: { fullSelector: this.targetElement.fullSelector },
                    mode: "walkthroughrendering"
                }, "*");
            }, data.payload.eventOptions );
        }
    }
    // updateTargetElementDimensions(payload) {
    //     this.targetElements[payload.selector].
    // }
}//$Id$



class InProduct_ChildMessageInitiator{
    static instance = null;
    static initialize(){
        if(!InProduct_ChildMessageInitiator.instance){
            InProduct_ChildMessageInitiator.instance = new InProduct_ChildMessageInitiator();
            InProduct_ChildMessageInitiator.instance.setConfiguration();    
        }
        return;
    }
    constructor(){
        this.connectorVersion = 1;
        this.isTopWindow = window.top == window;
        this.isIntermediateWindow = false;
        this.topSameOriginWindow = false;
        this.sendMsgInitInterval = null;
    }
    sendInitMsg(){
        window.parent.postMessage({source:"inproductsdk",action : "iframeRegister" , origin:"inproduct_childsdk" ,mode:"iframeRegistration",  data:{}} , "*");
    }
    setConfiguration(){
        this.sendInitMsg();
        InProduct_CrossOriginMessenger.initialize();
        InProduct_CrossOriginMessenger.instance.addEventListeners();
        try {
            var parentDocument = window.parent.document;
            this.isIntermediateWindow = true;
        }catch (e) {
            this.topSameOriginWindow = true;
            WalkthroughBuilderSDK.getInstance();
        } 
    }
    handleRegistrationSuccess(){
        if (this.sendMsgInitInterval) {
            clearInterval(this.sendMsgInitInterval);
            this.sendMsgInitInterval = null;
        }
    }
}
InProduct_ChildMessageInitiator.initialize();