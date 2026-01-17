#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>
#include <map>

using namespace std;

int n;

// Cache queries to avoid duplicates
map<vector<int>, int> cache_query;

int query(int k, const vector<int>& a) {
    vector<int> sorted_a = a;
    sort(sorted_a.begin(), sorted_a.end());
    if (cache_query.count(sorted_a)) return cache_query[sorted_a];

    cout << "? " << k;
    for (int x : sorted_a) cout << " " << x;
    cout << endl;
    
    int res;
    cin >> res;
    return cache_query[sorted_a] = res;
}

// Find combination of counts per bin to satisfy sum constraints
bool find_combination(int p, int target, int needed, const vector<int>& bin_counts, vector<int>& result) {
    result.assign(p, 0);
    
    auto solve = [&](auto&& self, int idx, int current_count, int current_sum) -> bool {
        if (current_count == needed) {
            return (current_sum % p == target);
        }
        if (idx == p) return false;
        
        int max_take = min(bin_counts[idx], needed - current_count);
        
        for (int take = max_take; take >= 0; --take) {
            result[idx] = take;
            if (self(self, idx + 1, current_count + take, (current_sum + take * idx) % p)) return true;
        }
        result[idx] = 0;
        return false;
    };
    
    return solve(solve, 0, 0, 0);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if (!(cin >> n)) return 0;

    vector<int> primes = {2, 3, 5, 7, 11};
    map<int, vector<int>> p_vals;

    for (int p : primes) {
        vector<vector<int>> bins(p);
        bins[0].push_back(1);
        vector<int> val(n + 1);
        val[1] = 0;

        for (int i = 2; i <= n; ++i) {
            vector<vector<int>> test_configs(p); 
            vector<bool> can_test(p, false);
            vector<int> bin_counts(p);
            for(int b=0; b<p; ++b) bin_counts[b] = bins[b].size();

            for (int r = 0; r < p; ++r) {
                int target = (p - r) % p;
                vector<int> counts;
                if (find_combination(p, target, p - 1, bin_counts, counts)) {
                    can_test[r] = true;
                    test_configs[r] = counts;
                }
            }
            
            vector<int> check_order;
            for(int r=0; r<p; ++r) if(can_test[r]) check_order.push_back(r);
            random_shuffle(check_order.begin(), check_order.end());

            int found = -1;
            int tested_count = 0;
            int total_testable = check_order.size();
            
            for (int r : check_order) {
                if (tested_count == total_testable - 1 && total_testable == p) {
                    found = r;
                    break;
                }

                vector<int> q_indices;
                q_indices.push_back(i);
                vector<int> counts = test_configs[r];
                for (int b = 0; b < p; ++b) {
                    for (int k = 0; k < counts[b]; ++k) {
                        q_indices.push_back(bins[b][k]); 
                    }
                }
                
                if (query(p, q_indices)) {
                    found = r;
                    break;
                }
                tested_count++;
            }
            
            if (found != -1) {
                bins[found].push_back(i);
                val[i] = found;
            } else {
                for (int r = 0; r < p; ++r) {
                    if (!can_test[r]) {
                        found = r;
                        break;
                    }
                }
                bins[found].push_back(i);
                val[i] = found;
            }
        }
        p_vals[p] = val;
    }

    map<int, vector<int>> inv_cache;
    for(int p : primes) {
        inv_cache[p].resize(p);
        for(int x=1; x<p; ++x) {
            for(int y=1; y<p; ++y) {
                if ((x*y)%p == 1) inv_cache[p][x] = y;
            }
        }
    }

    long long M = 1;
    for(int p : primes) M *= p;
    
    vector<long long> M_p(primes.size());
    vector<long long> y_p(primes.size());
    for(size_t k=0; k<primes.size(); ++k) {
        int p = primes[k];
        long long mk = M / p;
        M_p[k] = mk;
        long long y = 0;
        for(long long z=1; z<p; ++z) {
            if ((mk * z) % p == 1) {
                y = z;
                break;
            }
        }
        y_p[k] = y;
    }

    vector<int> limits;
    for(int p : primes) limits.push_back(p - 1);
    
    vector<int> s(primes.size(), 1);
    
    while(true) {
        vector<int> a_coeff(primes.size());
        for(size_t k=0; k<primes.size(); ++k) {
            a_coeff[k] = inv_cache[primes[k]][s[k]];
        }

        vector<long long> d(n + 1);
        long long min_d = M, max_d = -M;

        for(int i=1; i<=n; ++i) {
            long long val = 0;
            for(size_t k=0; k<primes.size(); ++k) {
                long long rem = (p_vals[primes[k]][i] * a_coeff[k]) % primes[k];
                val = (val + rem * M_p[k] * y_p[k]);
            }
            val %= M;
            if (val > M/2) val -= M;
            d[i] = val;
            if (val < min_d) min_d = val;
            if (val > max_d) max_d = val;
        }

        if (max_d - min_d == n - 1) {
            set<long long> distinct_vals;
            for(int i=1; i<=n; ++i) distinct_vals.insert(d[i]);
            if ((int)distinct_vals.size() == n) {
                vector<int> p_res(n + 1);
                long long p1 = 1 - min_d;
                if (p1 <= n/2) {
                    for(int i=1; i<=n; ++i) p_res[i] = p1 + d[i];
                } else {
                    for(int i=1; i<=n; ++i) p_res[i] = (n + 1) - (p1 + d[i]);
                }
                
                cout << "! ";
                for(int i=1; i<=n; ++i) cout << p_res[i] << (i==n ? "" : " ");
                cout << endl;
                return 0;
            }
        }

        int idx = 0;
        while(idx < (int)primes.size()) {
            s[idx]++;
            if (s[idx] > limits[idx]) {
                s[idx] = 1;
                idx++;
            } else {
                break;
            }
        }
        if (idx == (int)primes.size()) break;
    }

    return 0;
}