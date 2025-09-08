from fyers_apiv3 import fyersModel
import webbrowser

#### Generate an authcode and then make a request to generate an accessToken (Login Flow)

"""
1. Input parameters
"""
redirect_uri= "http://127.0.0.1:5000/callback" 
client_id = "MX3ZI638YI-100"     
secret_key = "2IC9MIKXVJ"         
grant_type = "authorization_code"          
response_type = "code"                             
state = "sample" 


### Connect to the sessionModel object here with the required input parameters
appSession = fyersModel.SessionModel(client_id = client_id, redirect_uri = redirect_uri,
                                     response_type=response_type,state=state,secret_key=secret_key,grant_type=grant_type)

# ## Make  a request to generate_authcode object this will return a login url which you need to open in your browser from where you can get the generated auth_code 
generateTokenUrl = appSession.generate_authcode()
print("Login URL: ", generateTokenUrl)
webbrowser.open(generateTokenUrl,new=1)


if generateTokenUrl:
    ### After succesfull login the user can copy the generated auth_code over here and make the request to generate the accessToken 
    auth_code = input("Please enter the Auth_Code here ==> ")
    appSession.set_token(auth_code)
    response = appSession.generate_token()

    ## There can be two cases over here you can successfully get the acccessToken over the request or you might get some error over here. so to avoid that have this in try except block
    try: 
        access_token = response["access_token"]

        print(f'Access Token: {access_token}')
        
    except Exception as e:
        print(e,response)  ## This will help you in debugging then and there itself like what was the error and also you would be able to see the value you got in response variable. instead of getting key_error for unsuccessfull response.




## Once you have generated accessToken now we can call multiple trading related or data related apis after that in order to do so we need to first initialize the fyerModel object with all the requried params.
"""
fyerModel object takes following values as arguments
1. accessToken : this is the one which you received from above 
2. client_id : this is basically the app_id for the particular app you logged into
"""
fyers = fyersModel.FyersModel(token=access_token,is_async=False,client_id=client_id,log_path="")



## After this point you can call the relevant apis and get started with

####################################################################################################################
"""
1. User Apis : This includes (Profile,Funds,Holdings)
"""

print(f'Customer Profile: \n {fyers.get_profile()['data']}')  ## This will provide us with the user related data 
print('\n')
print(f'Customer Account information: \n {fyers.funds()['fund_limit']}')        ## This will provide us with the funds the user has 
print('\n')
print(f'Customer Investment details: \n {fyers.holdings()['overall']}')    ## This will provide the available holdings the user has 
print('\n')
print("Fetching and filtering stocks...")


