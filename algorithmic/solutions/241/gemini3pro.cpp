#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <cmath>
#include <bitset>

using namespace std;

void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

struct Result {
    string expr;
    int cost; 
};

map<string, Result> memo;

bool is_monotone(int n, const string& s) {
    int len = s.length();
    for (int i = 0; i < len; ++i) {
        if (s[i] == '1') {
             for (int k = 0; k < n; ++k) {
                if (!((i >> k) & 1)) {
                    int neighbor = i | (1 << k);
                    if (s[neighbor] == '0') return false;
                }
            }
        }
    }
    return true;
}

vector<vector<int>> get_components(const string& tt, int num_vars, int type) {
    vector<vector<int>> comps;
    int len = tt.length();
    vector<int> valid_indices;
    valid_indices.reserve(len);
    for(int i=0; i<len; ++i) {
        if (type == 0) { 
            if (tt[i] == '0') valid_indices.push_back(i);
        } else { 
            if (tt[i] == '1') valid_indices.push_back(i);
        }
    }
    
    if (valid_indices.empty()) return {}; 
    
    vector<int> parent(num_vars);
    for(int i=0; i<num_vars; ++i) parent[i] = i;
    auto find = [&](int i) {
        while(i != parent[i]) { parent[i] = parent[parent[i]]; i = parent[i]; }
        return i;
    };
    auto unite = [&](int i, int j) {
        int root_i = find(i);
        int root_j = find(j);
        if (root_i != root_j) parent[root_i] = root_j;
    };
    
    int num_valid = valid_indices.size();
    int num_words = (num_valid + 63) / 64;
    vector<vector<uint64_t>> var_masks(num_vars, vector<uint64_t>(num_words, 0));
    
    for(int k=0; k<num_valid; ++k) {
        int idx = valid_indices[k];
        for(int v=0; v<num_vars; ++v) {
            if ((idx >> v) & 1) {
                var_masks[v][k/64] |= (1ULL << (k%64));
            }
        }
    }
    
    uint64_t last_mask = (num_valid % 64 == 0) ? ~0ULL : ((1ULL << (num_valid % 64)) - 1);

    for(int i=0; i<num_vars; ++i) {
        for(int j=i+1; j<num_vars; ++j) {
            bool has_00 = false, has_01 = false, has_10 = false, has_11 = false;
            
            for(int w=0; w<num_words; ++w) {
                uint64_t m_i = var_masks[i][w];
                uint64_t m_j = var_masks[j][w];
                uint64_t valid = (w == num_words - 1) ? last_mask : ~0ULL;
                
                if ((m_i & m_j & valid)) has_11 = true;
                if ((m_i & ~m_j & valid)) has_10 = true;
                if ((~m_i & m_j & valid)) has_01 = true;
                if ((~m_i & ~m_j & valid)) has_00 = true;
                
                if (has_11 && has_10 && has_01 && has_00) break;
            }
            
            if (!(has_11 && has_10 && has_01 && has_00)) {
                unite(i, j);
            }
        }
    }
    
    map<int, vector<int>> groups;
    for(int i=0; i<num_vars; ++i) {
        groups[find(i)].push_back(i);
    }
    
    for(auto& p : groups) {
        comps.push_back(p.second);
    }
    return comps;
}

string extract_sub_tt(const string& tt, int num_vars, const vector<int>& comp, int type) {
    int k = comp.size();
    int res_len = 1 << k;
    string res(res_len, ' ');
    
    vector<int> bit_map = comp;
    
    int fixed_val = (type == 0) ? 0 : 1;
    int fixed_mask = 0;
    int comp_mask = 0;
    for(int i : comp) comp_mask |= (1 << i);
    
    int all_mask = (1 << num_vars) - 1;
    int other_mask = all_mask ^ comp_mask;
    
    if (fixed_val == 1) fixed_mask = other_mask;
    
    for(int i=0; i<res_len; ++i) {
        int orig_idx = fixed_mask;
        for(int b=0; b<k; ++b) {
            if ((i >> b) & 1) {
                orig_idx |= (1 << bit_map[b]);
            }
        }
        res[i] = tt[orig_idx];
    }
    return res;
}

string project_tt(const string& s, int idx, char val) {
    int len = s.length();
    string res;
    res.reserve(len / 2);
    int val_bit = (val == '1' ? 1 : 0);
    for (int k = 0; k < len; ++k) {
        if (((k >> idx) & 1) == val_bit) {
            res.push_back(s[k]);
        }
    }
    return res;
}

Result solve(string tt, vector<string> var_names) {
    bool all0 = true, all1 = true;
    for(char c : tt) {
        if(c == '1') all0 = false;
        else all1 = false;
    }
    if(all0) return {"F", 0};
    if(all1) return {"T", 0};

    int n = 0;
    while((1<<n) < (int)tt.length()) n++;
    
    vector<int> active;
    for(int i=0; i<n; ++i) {
        bool depends = false;
        int stride = 1 << i;
        for(int j=0; j < (1<<n); ++j) {
            if (!((j >> i) & 1)) {
                if (tt[j] != tt[j | stride]) {
                    depends = true;
                    break;
                }
            }
        }
        if(depends) active.push_back(i);
    }
    
    vector<string> new_names;
    string compressed_tt;
    if ((int)active.size() < n) {
        int new_len = 1 << active.size();
        compressed_tt.resize(new_len);
        for(int i=0; i<new_len; ++i) {
            int orig_idx = 0;
            for(int b=0; b<(int)active.size(); ++b) {
                if((i >> b) & 1) orig_idx |= (1 << active[b]);
            }
            compressed_tt[i] = tt[orig_idx];
        }
        for(int idx : active) new_names.push_back(var_names[idx]);
        tt = compressed_tt;
        var_names = new_names;
        n = active.size();
    }
    
    if(memo.count(tt)) {
        Result r = memo[tt];
        string final_expr = "";
        for(size_t i=0; i<r.expr.length(); ++i) {
            if(r.expr[i] == '$') {
                i++;
                size_t j = i;
                while(j < r.expr.length() && isdigit(r.expr[j])) j++;
                int idx = stoi(r.expr.substr(i, j-i));
                final_expr += var_names[idx];
                i = j - 1;
            } else {
                final_expr += r.expr[i];
            }
        }
        return {final_expr, r.cost};
    }
    
    if (n == 0) return {"F", 0};
    if (n == 1) {
        Result r = {"$0", 0};
        memo[tt] = r;
        return {var_names[0], 0};
    }
    
    auto comps_or = get_components(tt, n, 0);
    if (comps_or.size() > 1) {
        string expr = "";
        int cost = 0;
        bool first = true;
        for (auto& c : comps_or) {
            string sub_tt = extract_sub_tt(tt, n, c, 0);
            vector<string> sub_names;
            for(int idx : c) sub_names.push_back(var_names[idx]); 
            
            Result sub_res = solve(sub_tt, sub_names);
            
            if (!first) {
                expr = "(" + expr + "|" + sub_res.expr + ")";
                cost += sub_res.cost + 1;
            } else {
                expr = sub_res.expr;
                cost += sub_res.cost;
                first = false;
            }
        }
        string templ = "";
        for(size_t i=0; i<expr.length(); ++i) {
            bool matched = false;
            for(int v=0; v<n; ++v) {
                if (expr.substr(i).find(var_names[v]) == 0) { 
                    string vn = var_names[v];
                    bool exact = true;
                    if (i + vn.length() < expr.length() && isalpha(expr[i+vn.length()])) exact = false;
                    if (exact) {
                        templ += "$" + to_string(v);
                        matched = true;
                        i += vn.length() - 1;
                        break;
                    }
                }
            }
            if(!matched) templ += expr[i];
        }
        memo[tt] = {templ, cost};
        return {expr, cost};
    }
    
    auto comps_and = get_components(tt, n, 1);
    if (comps_and.size() > 1) {
        string expr = "";
        int cost = 0;
        bool first = true;
        for (auto& c : comps_and) {
            string sub_tt = extract_sub_tt(tt, n, c, 1);
            vector<string> sub_names;
            for(int idx : c) sub_names.push_back(var_names[idx]);
            
            Result sub_res = solve(sub_tt, sub_names);
            
            if (!first) {
                expr = "(" + expr + "&" + sub_res.expr + ")";
                cost += sub_res.cost + 1;
            } else {
                expr = sub_res.expr;
                cost += sub_res.cost;
                first = false;
            }
        }
        string templ = "";
        for(size_t i=0; i<expr.length(); ++i) {
             bool matched = false;
            for(int v=0; v<n; ++v) {
                if (expr.substr(i).find(var_names[v]) == 0) {
                    string vn = var_names[v];
                    bool exact = true;
                    if (i + vn.length() < expr.length() && isalpha(expr[i+vn.length()])) exact = false;
                    if (exact) {
                        templ += "$" + to_string(v);
                        matched = true;
                        i += vn.length() - 1;
                        break;
                    }
                }
            }
            if(!matched) templ += expr[i];
        }
        memo[tt] = {templ, cost};
        return {expr, cost};
    }
    
    Result best_res = {"", 1000000};
    
    for(int i=0; i<n; ++i) {
        string tt0 = project_tt(tt, i, '0');
        string tt1 = project_tt(tt, i, '1');
        
        vector<string> sub_names;
        for(int k=0; k<n; ++k) if(k!=i) sub_names.push_back(var_names[k]);
        
        Result r0 = solve(tt0, sub_names);
        Result r1 = solve(tt1, sub_names);
        
        // Form 1: (x & f1) | f0
        string t1_expr; int t1_cost;
        if (r1.expr == "F") { t1_expr = "F"; t1_cost = 0; }
        else if (r1.expr == "T") { t1_expr = var_names[i]; t1_cost = 0; }
        else { t1_expr = "(" + var_names[i] + "&" + r1.expr + ")"; t1_cost = r1.cost + 1; }
        
        string res1_expr; int res1_cost;
        if (t1_expr == "T" || r0.expr == "T") { res1_expr = "T"; res1_cost = 0; }
        else if (t1_expr == "F") { res1_expr = r0.expr; res1_cost = r0.cost; }
        else if (r0.expr == "F") { res1_expr = t1_expr; res1_cost = t1_cost; }
        else { res1_expr = "(" + t1_expr + "|" + r0.expr + ")"; res1_cost = t1_cost + r0.cost + 1; }
        
        if (res1_cost < best_res.cost) best_res = {res1_expr, res1_cost};
        
        // Form 2: (x | f0) & f1
        string t2_expr; int t2_cost;
        if (r0.expr == "T") { t2_expr = "T"; t2_cost = 0; }
        else if (r0.expr == "F") { t2_expr = var_names[i]; t2_cost = 0; }
        else { t2_expr = "(" + var_names[i] + "|" + r0.expr + ")"; t2_cost = r0.cost + 1; }
        
        string res2_expr; int res2_cost;
        if (t2_expr == "F" || r1.expr == "F") { res2_expr = "F"; res2_cost = 0; }
        else if (t2_expr == "T") { res2_expr = r1.expr; res2_cost = r1.cost; }
        else if (r1.expr == "T") { res2_expr = t2_expr; res2_cost = t2_cost; }
        else { res2_expr = "(" + t2_expr + "&" + r1.expr + ")"; res2_cost = t2_cost + r1.cost + 1; }
        
        if (res2_cost < best_res.cost) best_res = {res2_expr, res2_cost};
    }
    
    string templ = "";
    for(size_t i=0; i<best_res.expr.length(); ++i) {
        bool matched = false;
        for(int v=0; v<n; ++v) {
            if (best_res.expr.substr(i).find(var_names[v]) == 0) {
                 string vn = var_names[v];
                 bool exact = true;
                 if (i + vn.length() < best_res.expr.length() && isalpha(best_res.expr[i+vn.length()])) exact = false;
                 if (exact) {
                    templ += "$" + to_string(v);
                    matched = true;
                    i += vn.length() - 1;
                    break;
                 }
            }
        }
        if(!matched) templ += best_res.expr[i];
    }
    memo[tt] = {templ, best_res.cost};
    
    return best_res;
}

void run_test() {
    int n;
    if (!(cin >> n)) return;
    string s;
    cin >> s;
    
    if (!is_monotone(n, s)) {
        cout << "No\n";
        return;
    }
    
    cout << "Yes\n";
    vector<string> names;
    for(int i=0; i<n; ++i) {
        string nm = "";
        nm += (char)('a' + i);
        names.push_back(nm);
    }
    
    Result r = solve(s, names);
    cout << r.expr << "\n";
}

int main() {
    fast_io();
    int t;
    if (cin >> t) {
        while(t--) {
            run_test();
        }
    }
    return 0;
}