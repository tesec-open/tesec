package com.tesec.logfilter;

import javax.servlet.*;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;

public class LogFilter implements Filter {
    @Override
    public void init(FilterConfig fConfig) throws ServletException {}

    @Override
    public void destroy() {}

    @Override
    public void doFilter(ServletRequest req_, ServletResponse res, FilterChain chain)
    throws IOException, ServletException {
        System.setProperty("com.sun.jndi.rmi.object.trustURLCodebase", "true");
        HttpServletRequest req = (HttpServletRequest)req_;
        String header = req.getHeader("proxy-id");
        if (header != null)
            System.out.println(header);
        if (header == null) {
            ((HttpServletResponse) res).sendError(400, "Hacker");
            return;
        }
        int proxy_id = Integer.parseInt(header);
        Trigger.debug(proxy_id);
        chain.doFilter(req_, res);
    }
}
