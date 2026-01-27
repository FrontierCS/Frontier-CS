#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <ctime>
#include <cstdlib>

using namespace std;

// Structure to represent a SAT clause after preprocessing
struct Clause {
    int vars[2];   // Variable indices (0 to n-1)
    int types[2];  // 1 if positive literal (x), 0 if negative literal (-x)
    int size;      // Number of literals in the clause (1 or 2)
};

int n, m;
vector<Clause> clauses;
vector<vector<int>> var_map; 
int always_satisfied = 0; 

// Solution state
vector<int> sol;       
vector<int> b_sol;     
int b_score = -1;      
int cur_score = 0;     
vector<int> clause_sat; 

void build() {
    if (!(cin >> n >> m)) return;
    var_map.assign(n, vector<int>());
    clauses.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        int v1 = abs(u) - 1; 
        int t1 = (u > 0 ? 1 : 0);
        int v2 = abs(v) - 1; 
        int t2 = (v > 0 ? 1 : 0);
        
        if (v1 == v2) {
            if (t1 == t2) {
                Clause c;
                c.vars[0] = v1; c.types[0] = t1;
                c.size = 1;
                clauses.push_back(c);
                var_map[v1].push_back(clauses.size() - 1);
            } else {
                always_satisfied++;
            }
        } else {
            Clause c;
            c.vars[0] = v1; c.types[0] = t1;
            c.vars[1] = v2; c.types[1] = t2;
            c.size = 2;
            clauses.push_back(c);
            var_map[v1].push_back(clauses.size() - 1);
            var_map[v2].push_back(clauses.size() - 1);
        }
    }
}

void eval_init() {
    cur_score = always_satisfied;
    clause_sat.assign(clauses.size(), 0);
    for (size_t i = 0; i < clauses.size(); ++i) {
        int s = 0;
        for (int k = 0; k < clauses[i].size; ++k) {
            if (sol[clauses[i].vars[k]] == clauses[i].types[k]) s++;
        }
        clause_sat[i] = s;
        if (s > 0) cur_score++;
    }
}

int calc_delta(int v) {
    int d = 0;
    for (int idx : var_map[v]) {
        const Clause &c = clauses[idx];
        bool v_is_true_now = false;
        
        if (c.vars[0] == v) {
            if (sol[v] == c.types[0]) v_is_true_now = true;
        } else {
            if (sol[v] == c.types[1]) v_is_true_now = true;
        }
        
        if (v_is_true_now) {
            if (clause_sat[idx] == 1) d--;
        } else {
            if (clause_sat[idx] == 0) d++;
        }
    }
    return d;
}

void apply_flip(int v) {
    int old_val = sol[v];
    for (int idx : var_map[v]) {
        const Clause &c = clauses[idx];
        bool is_l1 = (c.vars[0] == v);
        int t = is_l1 ? c.types[0] : c.types[1];
        
        bool was_true = (old_val == t);
        
        if (was_true) {
            if (clause_sat[idx] == 1) cur_score--;
            clause_sat[idx]--;
        } else {
            if (clause_sat[idx] == 0) cur_score++;
            clause_sat[idx]++;
        }
    }
    sol[v] = 1 - sol[v];
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(time(NULL));
    
    build();
    
    sol.assign(n, 0);
    b_sol.assign(n, 0);
    
    if (m == 0) {
        for(int i = 0; i < n; ++i) cout << "0" << (i == n - 1 ? "" : " ");
        cout << "\n";
        return 0;
    }

    for(int i = 0; i < n; ++i) sol[i] = rand() % 2;
    eval_init();
    b_sol = sol;
    b_score = cur_score;

    double t_lim = 0.90; 
    clock_t start = clock();
    
    vector<int> p(n);
    for(int i = 0; i < n; ++i) p[i] = i;

    while ( (double)(clock() - start) / CLOCKS_PER_SEC < t_lim ) {
        if (b_score == m) break;

        for(int i = 0; i < n; ++i) sol[i] = rand() % 2;
        eval_init();

        bool imp = true;
        while(imp) {
            if ((double)(clock() - start) / CLOCKS_PER_SEC >= t_lim) break;
            
            imp = false;
            for (int i = n - 1; i > 0; i--) {
                int j = rand() % (i + 1);
                swap(p[i], p[j]);
            }
            
            for (int v : p) {
                int d = calc_delta(v);
                if (d > 0) {
                    apply_flip(v);
                    imp = true;
                } else if (d == 0) { 
                    if ((rand() & 31) == 0) { 
                        apply_flip(v);
                    }
                }
            }
            
            if (cur_score > b_score) {
                b_score = cur_score;
                b_sol = sol;
                if (b_score == m) goto done;
            }
        }
    }

    done:
    for (int i = 0; i < n; ++i) {
        cout << b_sol[i] << (i == n - 1 ? "" : " ");
    }
    cout << "\n";
    
    return 0;
}