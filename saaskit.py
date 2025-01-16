import os
from domainMonitorDp import DomainMonitor
keywords = os.getenv('expression', 'intext:"saas kit"')
sites = ['twitter.com', 'youtube.com','tiktok.com','reddit.com']
monitor = DomainMonitor()

domain=os.getenv('domain').strip()
if domain: 
    if ',' in domain:
        sites=domain.strip().split(',') 
    else:
        sites=[domain]

if keywords=='':
    print('at least input one gossip keyword ')
    return 
if ',' in keywords:
    keywords=keywords.split(',')
else:
    keywords=[keywords]
for k in keywords:

    expression = k
    # expression = f"intext:{k}"
    # expression = f"intitle:{k}"
    
    monitor.sites=sites
    advanced_queries = {}
    for s in sites:
        advanced_queries[s] = f'{expression} site:{s}'
    print('==',advanced_queries)

    results_df = monitor.monitor_all_sites(time_ranges=None,advanced_queries=advanced_queries)
    os.makedirs('result', exist_ok=True)
    results_df.to_csv('result/report.csv')
    if not results_df.empty:
        print("\n=== 监控统计 ===")
        print(f"总计发现新页面: {len(results_df)}")
        print(results_df['site'].value_counts())
