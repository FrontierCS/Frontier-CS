#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <algorithm>
#include <cmath>

using namespace std;

typedef vector<uint64_t> BitTable;

// Helper to get bit from table
inline int get_bit(const BitTable& table, int idx) {
    return (table[idx >> 6] >> (idx & 63)) & 1;
}

// Set bit
inline void set_bit(BitTable& table, int idx, int val) {
    if (val) table[idx >> 6] |= (1ULL << (idx & 63));
    else table[idx >> 6] &= ~(1ULL << (idx & 63));
}

// Check monotonicity
bool is_monotone(const BitTable& table, int n) {
    int num_bits = 1 << n;
    int num_words = (num_bits + 63) / 64;
    
    for (int i = 0; i < n; ++i) {
        if (i < 6) {
            // Inside 64-bit word
            int stride = 1 << i;
            // Mask for bits where var i is 0
            // Pattern 0 at i, 1 at i+stride... repeated
            // e.g. i=0, 010101... -> mask 0x5555...
            uint64_t m = 0;
            for(int k=0; k<64; ++k) {
                if (!((k >> i) & 1)) m |= (1ULL << k);
            }
            
            for (int w = 0; w < num_words; ++w) {
                uint64_t val = table[w];
                uint64_t val0 = val & m; // bits where var is 0
                uint64_t val1 = (val >> stride) & m; // bits where var is 1, shifted to 0 positions
                // We want val0 <= val1 => val0 & ~val1 == 0
                if ((val0 & ~val1) != 0) return false;
            }
        } else {
            // Across words
            int word_stride = 1 << (i - 6);
            for (int w = 0; w < num_words; w += 2 * word_stride) {
                for (int k = 0; k < word_stride; ++k) {
                    if (w + k + word_stride >= num_words) break; 
                    uint64_t v0 = table[w + k];
                    uint64_t v1 = table[w + k + word_stride];
                    if ((v0 & ~v1) != 0) return false;
                }
            }
        }
    }
    return true;
}

// Check if constant
int check_const(const BitTable& table, int n) {
    // Returns 0 for F, 1 for T, -1 for non-const
    int num_bits = 1 << n;
    int num_words = (num_bits + 63) / 64;
    int first = table[0] & 1;
    
    for (int w = 0; w < num_words; ++w) {
        uint64_t expected = first ? ~0ULL : 0ULL;
        uint64_t val = table[w];
        if (w == num_words - 1 && (num_bits % 64 != 0)) {
            uint64_t mask = (1ULL << (num_bits % 64)) - 1;
            val &= mask;
            expected &= mask;
        }
        if (val != expected) return -1;
    }
    return first;
}

// Split table
pair<BitTable, BitTable> split_table(const BitTable& table, int n, int var_idx) {
    int sz = 1 << (n - 1);
    int words = (sz + 63) / 64;
    BitTable t0(words, 0), t1(words, 0);
    
    if (var_idx >= 6) {
        int word_stride = 1 << (var_idx - 6);
        int src = 0; 
        int dst = 0;
        int num_src_words = (1 << n) / 64;
        if (num_src_words == 0) num_src_words = 1; // Should not happen for var_idx >= 6
        
        while (src < num_src_words) {
            for(int k=0; k<word_stride; ++k) t0[dst+k] = table[src+k];
            src += word_stride;
            for(int k=0; k<word_stride; ++k) t1[dst+k] = table[src+k];
            src += word_stride;
            dst += word_stride;
        }
    } else {
        int dst_idx = 0;
        int stride = 1 << var_idx;
        int total = 1 << n;
        
        for (int i = 0; i < total; i += 2 * stride) {
            for (int k = 0; k < stride; ++k) {
                if (get_bit(table, i + k)) set_bit(t0, dst_idx, 1);
                if (get_bit(table, i + k + stride)) set_bit(t1, dst_idx, 1);
                dst_idx++;
            }
        }
    }
    return {t0, t1};
}

struct MemoRes {
    int cost;
    int split_var;
    int type; // 0=F, 1=T, 2=Split, 3=Irrelevant
};

map<BitTable, MemoRes> memo;

MemoRes solve(BitTable table, int n) {
    if (memo.count(table)) return memo[table];
    
    int c = check_const(table, n);
    if (c != -1) {
        return memo[table] = {0, -1, c};
    }
    
    for (int i = 0; i < n; ++i) {
        auto parts = split_table(table, n, i);
        if (parts.first == parts.second) {
            MemoRes res = solve(parts.first, n - 1);
            return memo[table] = {res.cost, i, 3};
        }
    }
    
    int min_cost = 2e9;
    int best_var = -1;
    
    for (int i = 0; i < n; ++i) {
        auto parts = split_table(table, n, i);
        MemoRes r0 = solve(parts.first, n - 1);
        MemoRes r1 = solve(parts.second, n - 1);
        
        int current_cost;
        bool f0_is_F = (r0.type == 0);
        bool f1_is_T = (r1.type == 1);
        
        if (f0_is_F && f1_is_T) {
             current_cost = 0;
        } else if (f0_is_F) {
            current_cost = r1.cost + 1;
        } else if (f1_is_T) {
            current_cost = r0.cost + 1;
        } else {
            current_cost = r0.cost + r1.cost + 2;
        }
        
        if (current_cost < min_cost) {
            min_cost = current_cost;
            best_var = i;
        }
    }
    
    return memo[table] = {min_cost, best_var, 2};
}

string construct(BitTable table, int n, vector<string> vars) {
    MemoRes res = memo[table];
    if (res.type == 0) return "F";
    if (res.type == 1) return "T";
    
    if (res.type == 3) {
        int skip = res.split_var;
        auto parts = split_table(table, n, skip);
        vars.erase(vars.begin() + skip);
        return construct(parts.first, n - 1, vars);
    }
    
    if (res.type == 2) {
        int v = res.split_var;
        string var_name = vars[v];
        
        auto parts = split_table(table, n, v);
        vector<string> sub_vars = vars;
        sub_vars.erase(sub_vars.begin() + v);
        
        MemoRes r0 = memo[parts.first];
        MemoRes r1 = memo[parts.second];
        
        bool f0_is_F = (r0.type == 0);
        bool f1_is_T = (r1.type == 1);
        
        if (f0_is_F && f1_is_T) {
            return var_name;
        }
        
        string s0 = construct(parts.first, n - 1, sub_vars);
        string s1 = construct(parts.second, n - 1, sub_vars);
        
        if (f0_is_F) {
            return "(" + var_name + "&" + s1 + ")";
        }
        if (f1_is_T) {
            return "(" + var_name + "|" + s0 + ")";
        }
        
        return "((" + var_name + "&" + s1 + ")|" + s0 + ")";
    }
    return "";
}

void solve_test_case() {
    int n;
    if (!(cin >> n)) return;
    string s;
    cin >> s;
    
    int num_bits = 1 << n;
    int num_words = (num_bits + 63) / 64;
    BitTable table(num_words, 0);
    
    for (int i = 0; i < num_bits; ++i) {
        if (s[i] == '1') {
            set_bit(table, i, 1);
        }
    }
    
    if (!is_monotone(table, n)) {
        cout << "No" << endl;
        return;
    }
    
    cout << "Yes" << endl;
    memo.clear();
    solve(table, n);
    
    vector<string> vars;
    for(int i=0; i<n; ++i) {
        string name = "";
        name += (char)('a' + i);
        vars.push_back(name);
    }
    
    cout << construct(table, n, vars) << endl;
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