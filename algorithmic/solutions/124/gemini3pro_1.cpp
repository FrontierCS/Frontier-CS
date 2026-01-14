#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <set>
#include <cstdlib>
#include <ctime>

using namespace std;

// Function to perform a query
int query(int k, const vector<int>& indices) {
    cout << "? " << k;
    for (int x : indices) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

// Function to output the answer
void answer(const vector<int>& p) {
    cout << "!";
    for (int x : p) cout << " " << x;
    cout << endl;
    exit(0);
}

int N;
vector<int> p_mod[17]; // Stores p[i] % m relative grouping

// Determine groups modulo 2
void solve_mod2() {
    p_mod[2].assign(N + 1, 0);
    for (int i = 2; i <= N; ++i) {
        int r = query(2, {1, i});
        if (r) p_mod[2][i] = 0; // Same parity as p[1]
        else p_mod[2][i] = 1;   // Different parity
    }
}

// Split group of modulo M into modulo 2M
void split_mod(int M) {
    int next_M = 2 * M;
    p_mod[next_M].assign(N + 1, -1);
    
    for (int r = 0; r < M; ++r) {
        vector<int> group;
        for (int i = 1; i <= N; ++i) {
            if (p_mod[M][i] == r) group.push_back(i);
        }
        if (group.empty()) continue;
        
        vector<int> sub0, sub1;
        vector<int> unknown = group;
        
        // Random base attempts to split the group
        // We expect roughly constant number of attempts to find a splitting base
        int attempts = 0;
        while (!unknown.empty() && attempts < 20) {
            if (sub0.empty() && sub1.empty()) {
                // Initial state for this group
            } else if (!sub0.empty()) {
                // If sub0 found, rest are sub1
                for (int x : unknown) sub1.push_back(x);
                unknown.clear();
                break;
            }

            vector<int> base;
            int needed = next_M - 1;
            // Generate random base
            int safety = 0;
            while(base.size() < needed && safety < 1000) {
                int x = rand() % N + 1;
                bool ok = true;
                for(int b : base) if(b==x) ok=false;
                if(ok) base.push_back(x);
                safety++;
            }
            if(base.size() < needed) break; // Should not happen

            vector<int> current_ones;
            vector<int> next_unknown;
            
            for (int x : unknown) {
                bool in_base = false;
                for(int b : base) if(b == x) in_base = true;
                if(in_base) {
                    next_unknown.push_back(x); 
                    continue;
                }
                
                vector<int> q_set = base;
                q_set.push_back(x);
                if (query(next_M, q_set)) {
                    current_ones.push_back(x);
                } else {
                    next_unknown.push_back(x);
                }
            }
            
            if (!current_ones.empty()) {
                for(int x : current_ones) sub0.push_back(x);
                // The ones that returned 0 are candidates for sub1, kept in unknown
                unknown = next_unknown;
            }
            attempts++;
        }
        
        // If failed to split, assume all in one sub-group (default sub0)
        // or remaining unknown are sub1 if sub0 was found.
        if (sub0.empty() && sub1.empty()) {
             for (int x : group) p_mod[next_M][x] = 2 * p_mod[M][x]; 
        } else {
             // If sub0 not empty, unknown became sub1 in loop or remains.
             // If loop exited with unknown not empty, assume sub1
             for (int x : sub0) p_mod[next_M][x] = 2 * p_mod[M][x];
             for (int x : sub1) p_mod[next_M][x] = 2 * p_mod[M][x] + 1;
             for (int x : unknown) p_mod[next_M][x] = 2 * p_mod[M][x] + 1;
        }
    }
}

// Solve for coprime moduli
void solve_coprime(int k) {
    p_mod[k].assign(N + 1, -1);
    vector<int> unassigned;
    for (int i = 1; i <= N; ++i) unassigned.push_back(i);
    
    int classes_found = 0;
    while (!unassigned.empty() && classes_found < k) {
        if (classes_found == k - 1) {
            for (int x : unassigned) p_mod[k][x] = classes_found;
            break;
        }
        
        vector<int> base;
        int safety = 0;
        while(base.size() < k - 1 && safety < 1000) {
            int x = rand() % N + 1;
            bool ok = true;
            for(int b : base) if(b==x) ok=false;
            if(ok) base.push_back(x);
            safety++;
        }
        
        vector<int> ones;
        vector<int> next_unassigned;
        for (int x : unassigned) {
             bool in_base = false;
             for(int b : base) if(b == x) in_base = true;
             if(in_base) {
                 next_unassigned.push_back(x);
                 continue;
             }
             
             vector<int> q_set = base;
             q_set.push_back(x);
             if (query(k, q_set)) {
                 ones.push_back(x);
             } else {
                 next_unassigned.push_back(x);
             }
        }
        
        if (!ones.empty()) {
            for (int x : ones) p_mod[k][x] = classes_found;
            classes_found++;
        }
        unassigned = next_unassigned;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(time(0));
    if (!(cin >> N)) return 0;
    
    // Choose moduli based on N
    vector<int> mods;
    if (N <= 60) mods = {4, 3, 5};
    else if (N <= 120) mods = {8, 3, 5};
    else if (N <= 420) mods = {4, 3, 5, 7};
    else mods = {8, 3, 5, 7};
    
    bool do_2 = false, do_4 = false, do_8 = false;
    for (int m : mods) {
        if (m == 4) do_4 = true;
        if (m == 8) do_8 = true;
    }
    
    // Always start with mod 2
    solve_mod2();
    
    // Iteratively refine mod 2 -> 4 -> 8
    if (do_4 || do_8) {
        split_mod(2); // 2 -> 4
        if (do_8) {
            split_mod(4); // 4 -> 8
        }
    }
    
    // Independent moduli
    for (int m : mods) {
        if (m == 3 || m == 5 || m == 7) {
            solve_coprime(m);
        }
    }
    
    // Prepare for CRT
    vector<int> final_mods;
    if (do_8) final_mods.push_back(8);
    else if (do_4) final_mods.push_back(4);
    else final_mods.push_back(2); 
    
    for (int m : mods) {
        if (m % 2 != 0) final_mods.push_back(m);
    }
    
    int num_combinations = 1;
    for (int m : final_mods) num_combinations *= m;
    
    // Brute force shifts
    for (int iter = 0; iter < num_combinations; ++iter) {
        int temp = iter;
        vector<int> shifts;
        for (int m : final_mods) {
            shifts.push_back(temp % m);
            temp /= m;
        }
        
        vector<int> P(N);
        vector<bool> seen(N + 1, false);
        bool ok = true;
        
        for (int i = 1; i <= N; ++i) {
            long long val = 0;
            long long M = 1;
            
            for (size_t k = 0; k < final_mods.size(); ++k) {
                int m = final_mods[k];
                int a = (p_mod[m][i] + shifts[k]) % m;
                
                // Solve val + M*y = a (mod m)
                int inv = 0;
                for (int z = 0; z < m; ++z) {
                    if ((M % m) * z % m == 1) { inv = z; break; }
                }
                
                int diff = (a - (val % m));
                if (diff < 0) diff += m;
                int y = (diff * inv) % m;
                
                val = val + M * y;
                M *= m;
            }
            
            if (val == 0) val = M;
            if (val > N || seen[val]) { ok = false; break; }
            seen[val] = true;
            P[i-1] = val;
        }
        
        if (ok) {
            if (P[0] > N/2) {
                for (int& x : P) x = N + 1 - x;
            }
            answer(P);
        }
    }

    return 0;
}