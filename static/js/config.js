const isLocalDevelopment = window.location.hostname === 'localhost' || 
                           window.location.hostname === '127.0.0.1' || 
                           window.location.protocol === 'file:';

const CONFIG = {
    API_URL: isLocalDevelopment ? 'http://localhost:8000' : window.location.origin
};