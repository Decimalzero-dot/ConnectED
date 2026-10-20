def client_ip(group, request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[-1].strip()   
    return request.META.get('REMOTE_ADDR', '')