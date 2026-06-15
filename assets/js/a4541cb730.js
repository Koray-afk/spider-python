/*$Id$*/
class HttpCall
{
/** Extremely Important **/
/** Please refrain from using async = false. **/ 
/** Executing http calls syncronously will cause the entire page to freeze. **/

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
	}

	setRequestBody(body) // body must be in string. We dont support FormData(), blob etc
 	{
		this.body = body;
	}
	setPath(path){
		var isBranded = sessionStorage.isbrandeddomain || (typeof micsUtilStoreFramework !== 'undefined' && micsUtilStoreFramework.isbrandeddomain);
		
		return this.domain 
		  ? this.domain + path 
		  : isBranded
			? `${location.protocol}//${location.host}/micse${path}`
			: `${location.protocol}//${location.host}${path}`;
		
	}  
	setStaticPath(path)
       {
                this.path = path;
       }
	makeHttpRequest(onresponsecallback, onerrorcallback)
	{
		var queryparam="";	
		var self = this;
		this.getextraparams();
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
            if (self.errorConfig.HttpError[httpStatus]) {
                var errorConfig = self.errorConfig.HttpError[httpStatus];
                if (errorConfig.onError) {
                    errorConfig.onError(); 
                }
            }
            if (typeof onresponsecallback === 'function') {
                onresponsecallback(this.xhr);
            }
        };

		this.xhr.onerror = function() {
			if(self.errorConfig.NetworkError.onError){
				self.errorConfig.NetworkError.onError();
			}
			onerrorcallback(this);
		}

		this.xhr.ontimeout = function() {
			if(self.errorConfig.TimeoutError.onError){
				self.errorConfig.TimeoutError.onError();
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
	makeHttpRequestForUDServer(onresponsecallback, onerrorcallback,mimeType){
		var queryparam="";	
		var self = this;
		for (let key of this.params.keys())
		{		
			queryparam+= (queryparam == "")?  (key +"="+encodeURIComponent(this.params.get(key))) : ("&"+key +"="+encodeURIComponent(this.params.get(key))) ;
		}
                this.xhr.open(this.http_method, (queryparam == "")? (this.path) : (this.path+"?"+queryparam), this.async);
		
	

		this.headers.set("X-ZCSRF-TOKEN","iamcsrcoo= "+this.getCSRFTokenFromCookie());		
		for (let key of this.headers.keys())
		{
			this.xhr.setRequestHeader(key, this.headers.get(key));
		}
		this.xhr.setRequestHeader("Content-Type", mimeType);
		this.xhr.onload = () => {
            var httpStatus = this.xhr.status;
            if (self.errorConfig.HttpError[httpStatus]) {
                var errorConfig = self.errorConfig.HttpError[httpStatus];
                if (errorConfig.onError) {
                    errorConfig.onError(); 
                }
            }
            if (typeof onresponsecallback === 'function') {
                onresponsecallback(this.xhr);
            }
        };
		this.xhr.onerror = function() {
			if(self.errorConfig.NetworkError.onError){
				self.errorConfig.NetworkError.onError();
			}
			onerrorcallback(this);
		}
		this.xhr.ontimeout = function() {
			if(self.errorConfig.TimeoutError.onError){
				self.errorConfig.TimeoutError.onError();
			}
		}
		if(this.body == undefined)
		{
			this.xhr.withCredentials=true;
			this.xhr.send();
		}
		else
		{
			this.xhr.withCredentials=true;
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


        getextraparams(){
            const zsoid = sessionStorage.getItem("zsoid")
                || (typeof micsUtilStoreFramework !== 'undefined'
                    && micsUtilStoreFramework.getItem
                    && micsUtilStoreFramework.getItem("zsoid"))
                || null;
            if(zsoid && zsoid != null && zsoid != "undefined"){
                this.params.has("zsoid") ? '' : this.params.set("zsoid",zsoid);
            }
        }

        
		getOrgId() {
			var orgid = sessionStorage.getItem("orgid") 
				|| (typeof micsUtilStoreFramework !== 'undefined' 
					&& micsUtilStoreFramework.getItem 
					&& micsUtilStoreFramework.getItem("orgid"));
		
			return orgid == null ? -1 : orgid;
		}
        
		getForMicsE() {
			const forMicsE = sessionStorage.getItem("forMicsE") 
				|| (typeof micsUtilStoreFramework !== 'undefined' 
					&& micsUtilStoreFramework.getItem 
					&& micsUtilStoreFramework.getItem("forMicsE")) 
				|| null;
		
			return forMicsE === null ? false : forMicsE;
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

		setCustomErrorConfigurationByType(errorConfigType,onError){
			this.errorConfig[errorConfigType].onError = onError;
		}

    setCustomOnHttpErrorConfigurationByType(key,errorConfig){
      this.errorConfig.HttpError[key]=errorConfig;
    }

		setCustomOnHttpErrorConfiguration(onError){
				// this.errorConfig.HttpError[key].onError = onError;
				for (let key in this.errorConfig.HttpError){
					this.errorConfig.HttpError[key].onError = onError;
				}
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
