import os
from domainMonitorDp import DomainMonitor

def gossip():
    # Retrieve keywords and domain from environment variables or use default
    keywords = os.getenv('expression', 'intext:"saas kit"')
    sites = ['twitter.com', 'youtube.com', 'tiktok.com', 'reddit.com']

    # Initialize DomainMonitor instance
    monitor = DomainMonitor()

    # Retrieve and process the 'domain' environment variable
    domain = os.getenv('domain', '').strip()
    if domain:
        if domain=='':
            pass
            print('no target domain input')
        elif ',' in domain:
            print('more than 1 target domain input')

            sites = [d.strip() for d in domain.split(',')]
        else:
            print('1 target domain input')
            
            sites = [domain]
    print('=====sites',sites)

    # Ensure at least one keyword is provided
    if not keywords:
        print('At least input one gossip keyword.')
        return

    # Split keywords if multiple are provided
    if ',' in keywords:
        keywords = [k.strip() for k in keywords.split(',')]
    else:
        keywords = [keywords]

    # Iterate through each keyword to construct and execute search queries
    for k in keywords:
        expression = k
        monitor.sites = sites
        advanced_queries = {}

        # Construct search queries for each site
        for s in sites:
            advanced_queries[s] = f'{expression} site:{s}'

        # Print constructed queries for debugging
        print('==', advanced_queries)

        # Perform monitoring and collect results
        results_df = monitor.monitor_all_sites(time_ranges=None, advanced_queries=advanced_queries)
        
        # Save results to CSV
        os.makedirs('result', exist_ok=True)
        results_df.to_csv('result/report.csv', index=False)

        # Output monitoring statistics if results are found
        if not results_df.empty:
            print("\n=== 监控统计 ===")
            print(f"总计发现新页面: {len(results_df)}")
            print(results_df['site'].value_counts())

if __name__ == "__main__":
    gossip()
