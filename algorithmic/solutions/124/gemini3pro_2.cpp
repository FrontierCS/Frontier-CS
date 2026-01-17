#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <random>
#include <set>

using namespace std;

int n;
mt19937 rng(1337);

bool query(int k, const vector<int>& indices) {
    cout << "? " << k;
    for (int x : indices) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res == 1;
}

// Solve for a specific modulus k
// Returns a vector where res[i] is the relative residue of p[i] mod k
// The residue is normalized such that res[1] = 0.
vector<int> solve_mod(int k) {
    vector<int> unclassified;
    for (int i = 1; i <= n; ++i) unclassified.push_back(i);

    // Step 1: Find a base group G0
    vector<int> G0;
    while (true) {
        vector<int> pivot;
        vector<int> candidates = unclassified; 
        shuffle(candidates.begin(), candidates.end(), rng);
        if (candidates.size() < (size_t)(k - 1)) {
            // Should not happen given constraints
        }
        for(int i=0; i<k-1; ++i) pivot.push_back(candidates[i]);
        
        bool hit = false;
        int test_limit = min((int)candidates.size() - (k-1), 20);
        for (int i = k-1; i < k-1 + test_limit; ++i) {
            vector<int> q = pivot;
            q.push_back(candidates[i]);
            if (query(k, q)) {
                hit = true;
                break;
            }
        }
        
        if (hit) {
            vector<int> new_unclassified;
            for (int x : unclassified) {
                bool in_pivot = false;
                for (int p : pivot) if (p == x) in_pivot = true;
                if (in_pivot) {
                    new_unclassified.push_back(x);
                    continue;
                }
                
                vector<int> q = pivot;
                q.push_back(x);
                if (query(k, q)) {
                    G0.push_back(x);
                } else {
                    new_unclassified.push_back(x);
                }
            }
            unclassified = new_unclassified;
            if (!G0.empty()) break;
        }
    }
    
    map<int, vector<int>> groups;
    for(int x : G0) groups[0].push_back(x);
    
    while(!unclassified.empty()) {
        if (groups.size() == 1) {
            int u = unclassified.back(); unclassified.pop_back();
            groups[1].push_back(u); 
            
            if (groups[0].size() < (size_t)(k - 2)) exit(1);
            
            vector<int> pivot;
            pivot.push_back(u);
            for(int i=0; i<k-2; ++i) pivot.push_back(groups[0][i]);
            
            vector<int> next_unclassified;
            for(int x : unclassified) {
                vector<int> q = pivot;
                q.push_back(x);
                if (query(k, q)) {
                    groups[(k-1)%k].push_back(x);
                } else {
                    next_unclassified.push_back(x);
                }
            }
            unclassified = next_unclassified;
        } else {
            int target = -1;
            for(int r=0; r<k; ++r) {
                if(groups.find(r) == groups.end()) {
                    target = r;
                    break;
                }
            }
            if (target == -1) target = rng() % k;
            
            int needed = (k - target) % k;
            
            vector<int> pivot;
            vector<pair<int,int>> pool;
            for(auto& p : groups) {
                for(int idx : p.second) pool.push_back({idx, p.first});
            }
            
            bool found_pivot = false;
            while(!found_pivot) {
                shuffle(pool.begin(), pool.end(), rng);
                int s = 0;
                if (pool.size() < (size_t)(k-1)) break;
                for(int i=0; i<k-1; ++i) s = (s + pool[i].second) % k;
                if (s == needed) {
                    for(int i=0; i<k-1; ++i) pivot.push_back(pool[i].first);
                    found_pivot = true;
                }
            }
            
            if (found_pivot) {
                vector<int> next_unclassified;
                for(int x : unclassified) {
                    vector<int> q = pivot;
                    q.push_back(x);
                    if (query(k, q)) {
                        groups[target].push_back(x);
                    } else {
                        next_unclassified.push_back(x);
                    }
                }
                unclassified = next_unclassified;
            }
        }
    }
    
    int shift = 0;
    for(auto& p : groups) {
        for(int x : p.second) {
            if (x == 1) {
                shift = p.first;
                break;
            }
        }
    }
    
    vector<int> res(n+1);
    for(auto& p : groups) {
        int val = (p.first - shift + k) % k;
        for(int x : p.second) res[x] = val;
    }
    return res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> n)) return 0;

    if (n == 2) {
        cout << "! 1 2" << endl;
        return 0;
    }
    
    vector<int> primes = {2, 3, 5, 7, 11};
    if (n <= 6) primes = {2, 3}; 
    else if (n <= 30) primes = {2, 3, 5}; 
    else if (n <= 210) primes = {2, 3, 5, 7}; 
    
    vector<int> mods = primes;
    vector<vector<int>> residues;
    for (int k : mods) {
        residues.push_back(solve_mod(k));
    }
    
    vector<int> current_mults(mods.size(), 1);
    
    auto check = [&](const vector<int>& mults) -> vector<int> {
        long long M = 1;
        for(int k : mods) M *= k;
        
        vector<long long> term_factor(mods.size());
        for(size_t j=0; j<mods.size(); ++j) {
            long long Nj = M / mods[j];
            int yj = 0;
            for(int t=0; t<mods[j]; ++t) {
                if ((Nj * t) % mods[j] == 1) {
                    yj = t;
                    break;
                }
            }
            term_factor[j] = (Nj * yj) % M;
        }
        
        vector<long long> V(n+1);
        for(int i=1; i<=n; ++i) {
            long long val = 0;
            for(size_t j=0; j<mods.size(); ++j) {
                int rem = (mults[j] * residues[j][i]) % mods[j];
                val = (val + rem * term_factor[j]) % M;
            }
            V[i] = val;
        }
        
        vector<long long> sortedV;
        for(int i=1; i<=n; ++i) sortedV.push_back(V[i]);
        sort(sortedV.begin(), sortedV.end());
        
        int jumps = 0;
        int gap_idx = -1;
        for(int j=0; j<n-1; ++j) {
            long long d = sortedV[j+1] - sortedV[j];
            if (d != 1) {
                jumps++;
                gap_idx = j;
            }
        }
        long long wrap_diff = (sortedV[0] + M) - sortedV[n-1];
        if (wrap_diff != 1) {
            jumps++;
            gap_idx = n-1;
        }
        
        if (jumps == 1) {
            long long start_val = sortedV[(gap_idx+1)%n];
            long long p1 = (1 - start_val + M) % M;
            if (p1 == 0) p1 = M;
            
            if (p1 >= 1 && p1 <= n/2) {
                vector<int> res(n+1);
                for(int i=1; i<=n; ++i) {
                    long long val = (p1 + V[i]);
                    val = (val - 1 + M) % M + 1;
                    if (val > n) return {};
                    res[i] = val;
                }
                return res;
            }
        }
        return {};
    };
    
    auto run_loops = [&](auto&& self, int idx) -> void {
        if (idx == (int)mods.size()) {
            vector<int> sol = check(current_mults);
            if (!sol.empty()) {
                cout << "! ";
                for(int i=1; i<=n; ++i) cout << sol[i] << (i==n?"":" ");
                cout << endl;
                exit(0);
            }
            return;
        }
        for(int m=1; m<mods[idx]; ++m) {
            current_mults[idx] = m;
            self(self, idx+1);
        }
    };
    
    run_loops(run_loops, 1);
    
    return 0;
}