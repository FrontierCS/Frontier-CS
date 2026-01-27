#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>

using namespace std;

// Represents the result of a solve step
struct Result {
    int cost;
    string expr;
    vector<bool> table; // Truth table of the result
};

// Memoization table
// Key: pair of L and U truth tables
// Value: Result
map<pair<vector<bool>, vector<bool>>, Result> memo;

// Check if a truth table corresponds to a monotonic function
bool is_monotonic(const vector<bool>& t, int n_vars) {
    int len = t.size();
    for (int i = 0; i < n_vars; ++i) {
        int stride = 1 << i;
        for (int j = 0; j < len; ++j) {
            if ((j & stride) == 0) {
                // bit i is 0 at j, 1 at j + stride
                // Monotonicity requires t[0] <= t[1] i.e. not (1 and 0)
                if (t[j] && !t[j + stride]) return false;
            }
        }
    }
    return true;
}

// Compute the smallest monotonic function >= target
vector<bool> monotonic_closure(vector<bool> t, int n_vars) {
    int len = t.size();
    bool changed = true;
    while(changed) {
        changed = false;
        for (int i = 0; i < n_vars; ++i) {
            int stride = 1 << i;
            for (int j = 0; j < len; ++j) {
                if ((j & stride) == 0) {
                    // if t[j]=1 and t[j+stride]=0, set t[j+stride]=1
                    if (t[j] && !t[j + stride]) {
                        t[j + stride] = true;
                        changed = true;
                    }
                }
            }
        }
    }
    return t;
}

// Compute the largest monotonic function <= target
vector<bool> monotonic_core(vector<bool> t, int n_vars) {
    int len = t.size();
    bool changed = true;
    while(changed) {
        changed = false;
        for (int i = 0; i < n_vars; ++i) {
            int stride = 1 << i;
            for (int j = 0; j < len; ++j) {
                if ((j & stride) == 0) {
                    // if t[j]=1 and t[j+stride]=0, set t[j]=0
                    if (t[j] && !t[j + stride]) {
                        t[j] = false;
                        changed = true;
                    }
                }
            }
        }
    }
    return t;
}

// Check if variable at index var_idx is relevant
bool is_relevant(const vector<bool>& t, int var_idx) {
    int len = t.size();
    int stride = 1 << var_idx;
    for (int j = 0; j < len; ++j) {
        if ((j & stride) == 0) {
            if (t[j] != t[j + stride]) return true;
        }
    }
    return false;
}

// Contract table by removing an irrelevant variable
vector<bool> contract(const vector<bool>& t, int var_idx) {
    int len = t.size();
    int stride = 1 << var_idx;
    vector<bool> res;
    res.reserve(len / 2);
    for (int j = 0; j < len; ++j) {
        if ((j & stride) == 0) {
            res.push_back(t[j]);
        }
    }
    return res;
}

// Split table into 0-half and 1-half for a variable
pair<vector<bool>, vector<bool>> split_table(const vector<bool>& t, int var_idx) {
    int len = t.size();
    int stride = 1 << var_idx;
    vector<bool> t0, t1;
    t0.reserve(len/2);
    t1.reserve(len/2);
    for (int j = 0; j < len; ++j) {
        if ((j & stride) == 0) {
            t0.push_back(t[j]);
            t1.push_back(t[j + stride]);
        }
    }
    return {t0, t1};
}

Result solve(vector<bool> L, vector<bool> U, vector<string> vars) {
    // 1. Remove irrelevant variables
    int n = vars.size();
    {
        bool changed = true;
        while(changed) {
            changed = false;
            if (vars.empty()) break;
            n = vars.size();
            for (int i = 0; i < n; ++i) {
                if (!is_relevant(L, i) && !is_relevant(U, i)) {
                    L = contract(L, i);
                    U = contract(U, i);
                    vars.erase(vars.begin() + i);
                    changed = true;
                    break; 
                }
            }
        }
    }
    n = vars.size();
    
    // 2. Normalization
    L = monotonic_closure(L, n);
    U = monotonic_core(U, n);
    
    // Check feasibility
    for(size_t i=0; i<L.size(); ++i) {
        if(L[i] && !U[i]) {
            return {1000000, "", {}}; 
        }
    }

    // 3. Base cases
    bool all_L_0 = true;
    for(bool b : L) if(b) { all_L_0 = false; break; }
    if (all_L_0) {
        return {0, "F", vector<bool>(1 << n, false)};
    }
    
    bool all_U_1 = true;
    for(bool b : U) if(!b) { all_U_1 = false; break; }
    if (all_U_1) {
        return {0, "T", vector<bool>(1 << n, true)};
    }

    if (memo.count({L, U})) return memo[{L, U}];

    // Check single variables
    for (int i = 0; i < n; ++i) {
        vector<bool> v_tab(1 << n);
        int stride = 1 << i;
        for (int j = 0; j < (1 << n); ++j) {
            if (j & stride) v_tab[j] = true;
            else v_tab[j] = false;
        }
        bool ok = true;
        for (size_t k = 0; k < L.size(); ++k) {
            if (L[k] && !v_tab[k]) { ok = false; break; }
            if (v_tab[k] && !U[k]) { ok = false; break; }
        }
        if (ok) {
            Result res = {0, vars[i], v_tab};
            memo[{L, U}] = res;
            return res;
        }
    }

    // 4. Recursive Step
    Result bestRes = {1000000, "", {}};

    for (int i = 0; i < n; ++i) {
        string v_name = vars[i];
        auto [L0, L1] = split_table(L, i);
        auto [U0, U1] = split_table(U, i);
        
        vector<string> next_vars = vars;
        next_vars.erase(next_vars.begin() + i);
        
        // Decomp 1: A | (v & B)
        Result resA = solve(L0, U0, next_vars);
        if (resA.cost < 1000000) {
            vector<bool> LB_B = L1;
            for(size_t k=0; k<LB_B.size(); ++k) {
                if (resA.table[k]) LB_B[k] = false; 
            }
            Result resB = solve(LB_B, U1, next_vars);
            if (resB.cost < 1000000) {
                string expr;
                int current_cost;
                
                if (resA.expr == "F") {
                    if (resB.expr == "T") { // v & T -> v
                         expr = v_name; current_cost = 0;
                    } else if (resB.expr == "F") { // v & F -> F
                         expr = "F"; current_cost = 0;
                    } else {
                         expr = "(" + v_name + "&" + resB.expr + ")";
                         current_cost = 1 + resB.cost;
                    }
                } else if (resB.expr == "F") { // A | F -> A
                    expr = resA.expr; current_cost = resA.cost;
                } else {
                    string term2;
                    int cost2;
                    if (resB.expr == "T") { term2 = v_name; cost2 = 0; }
                    else { term2 = "(" + v_name + "&" + resB.expr + ")"; cost2 = 1 + resB.cost; }
                    
                    if (resA.expr == "T") { expr = "T"; current_cost = 0; }
                    else { expr = "(" + resA.expr + "|" + term2 + ")"; current_cost = resA.cost + 1 + cost2; }
                }

                if (current_cost < bestRes.cost) {
                    vector<bool> tab(1 << n);
                    int stride = 1 << i;
                    for(int j=0; j<(1<<n); ++j) {
                        int sub_idx = (j & ((1<<i)-1)) | ((j >> (i+1)) << i);
                        if ((j & stride) == 0) { // v=0
                            tab[j] = resA.table[sub_idx];
                        } else { // v=1
                            tab[j] = resA.table[sub_idx] | resB.table[sub_idx];
                        }
                    }
                    bestRes = {current_cost, expr, tab};
                }
            }
        }

        // Decomp 2: A & (v | B)
        resA = solve(L1, U1, next_vars);
        if (resA.cost < 1000000) {
            vector<bool> UB_B = U0;
            for(size_t k=0; k<UB_B.size(); ++k) {
                if (!resA.table[k]) UB_B[k] = true;
            }
            Result resB = solve(L0, UB_B, next_vars);
            if (resB.cost < 1000000) {
                string expr;
                int current_cost;
                
                string term2;
                int cost2;
                if (resB.expr == "F") { term2 = v_name; cost2 = 0; }
                else if (resB.expr == "T") { term2 = "T"; cost2 = 0; }
                else { term2 = "(" + v_name + "|" + resB.expr + ")"; cost2 = 1 + resB.cost; }
                
                if (term2 == "T") { 
                    expr = resA.expr; current_cost = resA.cost;
                } else if (resA.expr == "F") {
                    expr = "F"; current_cost = 0;
                } else if (resA.expr == "T") {
                    expr = term2; current_cost = cost2;
                } else {
                    expr = "(" + resA.expr + "&" + term2 + ")";
                    current_cost = resA.cost + 1 + cost2;
                }

                if (current_cost < bestRes.cost) {
                     vector<bool> tab(1 << n);
                     int stride = 1 << i;
                     for(int j=0; j<(1<<n); ++j) {
                        int sub_idx = (j & ((1<<i)-1)) | ((j >> (i+1)) << i);
                        if ((j & stride) != 0) { // v=1
                            tab[j] = resA.table[sub_idx];
                        } else { // v=0
                            tab[j] = resA.table[sub_idx] & resB.table[sub_idx];
                        }
                     }
                     bestRes = {current_cost, expr, tab};
                }
            }
        }
    }
    
    memo[{L, U}] = bestRes;
    return bestRes;
}

void solve_test_case() {
    int n;
    cin >> n;
    string s;
    cin >> s;
    
    int len = 1 << n;
    vector<bool> table(len);
    for (int i = 0; i < len; ++i) table[i] = (s[i] == '1');
    
    if (!is_monotonic(table, n)) {
        cout << "No" << endl;
        return;
    }
    
    memo.clear();
    vector<string> vars(n);
    for(int i=0; i<n; ++i) {
        vars[i] = string(1, 'a' + i);
    }
    
    Result res = solve(table, table, vars);
    
    if (res.cost >= 1000000) {
        cout << "No" << endl;
    } else {
        cout << "Yes" << endl;
        cout << res.expr << endl;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while(t--) {
            solve_test_case();
        }
    }
    return 0;
}