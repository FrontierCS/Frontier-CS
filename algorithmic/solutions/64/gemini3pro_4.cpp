#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <ctime>
#include <random>
#include <string>

using namespace std;

typedef long long ll;

struct Element {
    ll val;
    int id;
};

int n;
ll T;
vector<Element> a;

ll best_diff = -1;
string best_sol;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> T)) return 0;
    a.resize(n);
    for(int i=0; i<n; ++i) {
        cin >> a[i].val;
        a[i].id = i;
    }

    best_diff = T + 1; // Initialize with a value larger than any possible error if T >= 0
    // Actually error can be T if we pick nothing. 
    // Just ensure first update takes it.
    // Let's manually check empty set
    best_diff = abs(T);
    best_sol = string(n, '0');

    if (n <= 46) {
        int n1 = n / 2;
        int n2 = n - n1;
        
        vector<pair<ll, int>> left_sums;
        left_sums.reserve(1 << n1);
        
        for(int i=0; i < (1<<n1); ++i) {
            ll s = 0;
            for(int j=0; j<n1; ++j) {
                if((i >> j) & 1) s += a[j].val;
            }
            left_sums.push_back({s, i});
        }
        sort(left_sums.begin(), left_sums.end());
        
        for(int i=0; i < (1<<n2); ++i) {
            ll s = 0;
            for(int j=0; j<n2; ++j) {
                if((i >> j) & 1) s += a[n1 + j].val;
            }
            
            ll target = T - s;
            auto it = lower_bound(left_sums.begin(), left_sums.end(), make_pair(target, -1));
            
            if(it != left_sums.end()) {
                ll total = s + it->first;
                ll diff = abs(total - T);
                if (diff < best_diff) {
                    best_diff = diff;
                    string res(n, '0');
                    int mask = it->second;
                    for(int j=0; j<n1; ++j) if((mask>>j)&1) res[a[j].id] = '1';
                    for(int j=0; j<n2; ++j) if((i>>j)&1) res[a[n1+j].id] = '1';
                    best_sol = res;
                }
            }
            if(it != left_sums.begin()) {
                auto it2 = prev(it);
                ll total = s + it2->first;
                ll diff = abs(total - T);
                if (diff < best_diff) {
                    best_diff = diff;
                    string res(n, '0');
                    int mask = it2->second;
                    for(int j=0; j<n1; ++j) if((mask>>j)&1) res[a[j].id] = '1';
                    for(int j=0; j<n2; ++j) if((i>>j)&1) res[a[n1+j].id] = '1';
                    best_sol = res;
                }
            }
            if(best_diff == 0) break;
        }
    } else {
        mt19937 rng(1337);
        shuffle(a.begin(), a.end(), rng);
        
        int K = 44;
        int n1 = K / 2; 
        int n2 = K - n1;
        int n_rest = n - K;
        
        vector<pair<ll, int>> S1;
        S1.reserve(1 << n1);
        for(int i=0; i < (1<<n1); ++i) {
            ll s = 0;
            for(int j=0; j<n1; ++j) {
                if((i >> j) & 1) s += a[j].val;
            }
            S1.push_back({s, i});
        }
        sort(S1.begin(), S1.end());
        
        vector<pair<ll, int>> S2;
        S2.reserve(1 << n2);
        for(int i=0; i < (1<<n2); ++i) {
            ll s = 0;
            for(int j=0; j<n2; ++j) {
                if((i >> j) & 1) s += a[n1 + j].val;
            }
            S2.push_back({s, i});
        }
        sort(S2.begin(), S2.end());
        
        clock_t start = clock();
        vector<int> rest_mask(n_rest);
        
        while(true) {
            if(best_diff == 0) break;
            if((double)(clock() - start) / CLOCKS_PER_SEC > 0.9) break;
            
            ll current_base = 0;
            for(int i=0; i<n_rest; ++i) {
                int bit = rng() & 1;
                rest_mask[i] = bit;
                if(bit) current_base += a[K + i].val;
            }
            
            ll target = T - current_base;
            
            int p1 = 0;
            int p2 = (int)S2.size() - 1;
            
            while(p1 < S1.size() && p2 >= 0) {
                ll val = S1[p1].first + S2[p2].first;
                ll diff = abs(val - target);
                
                if(diff < best_diff) {
                    best_diff = diff;
                    string res(n, '0');
                    int m1 = S1[p1].second;
                    int m2 = S2[p2].second;
                    
                    for(int j=0; j<n1; ++j) if((m1>>j)&1) res[a[j].id] = '1';
                    for(int j=0; j<n2; ++j) if((m2>>j)&1) res[a[n1+j].id] = '1';
                    for(int j=0; j<n_rest; ++j) if(rest_mask[j]) res[a[K+j].id] = '1';
                    
                    best_sol = res;
                    if(best_diff == 0) goto end_loops;
                }
                
                if(val < target) {
                    p1++;
                } else {
                    p2--;
                }
            }
        }
    }
    
    end_loops:
    cout << best_sol << endl;
    
    return 0;
}