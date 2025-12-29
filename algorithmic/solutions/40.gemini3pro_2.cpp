#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <map>
#include <cstdlib>

using namespace std;

// Calculate f(s): number of regular bracket substrings
int count_rbs(const string& s) {
    int n = s.length();
    int total = 0;
    for (int i = 0; i < n; ++i) {
        int balance = 0;
        for (int j = i; j < n; ++j) {
            if (s[j] == '(') balance++;
            else balance--;
            if (balance < 0) break;
            if (balance == 0) total++;
        }
    }
    return total;
}

// Generate a pattern for m variables
// Returns a vector where -1 is filler, 0..m-1 are variables
vector<int> find_pattern(int m) {
    // Random search for a pattern that distinguishes all 2^m states
    while (true) {
        int len = 14 + rand() % 8; // Try lengths around 14-21
        vector<int> p(len);
        for (int i = 0; i < len; ++i) {
            if (rand() % 3 == 0) p[i] = -1; // filler
            else p[i] = rand() % m; // variable
        }
        
        map<int, int> counts;
        bool ok = true;
        int num_states = 1 << m;
        
        // Simulate all outcomes assuming filler is ')' and variables are '(' or ')'
        // Mask bit 1 -> '(', bit 0 -> ')'
        for (int mask = 0; mask < num_states; ++mask) {
            string s = "";
            for (int x : p) {
                if (x == -1) {
                    s += ')'; 
                } else {
                    if ((mask >> x) & 1) s += '(';
                    else s += ')';
                }
            }
            int res = count_rbs(s);
            if (counts.count(res)) {
                ok = false;
                break;
            }
            counts[res] = mask;
        }
        
        if (ok) return p;
    }
}

int query(const vector<int>& indices) {
    cout << "0 " << indices.size();
    for (int x : indices) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0); // Should not happen if logic is correct
    return res;
}

void solve_case(int n) {
    // 1. Determine s[1]
    // We query sequences of form "s_i s_1".
    // If s_1 is ')', then s_i s_1 is "x )". If x='(', we get "()", count increases.
    // If s_1 is '(', then s_i s_1 is "x (". This generally does not form RBS easily as filler.
    // Specifically, if s_1='(', using it as filler in "x s_1 x s_1..." creates strictly increasing balance.
    // So if any query result > 0, s_1 must be ')'.
    // If all are 0, s_1 is '('. (Because s contains at least one '(', if s_1 was ')', we'd find it).
    
    bool s1_is_close = false;
    vector<int> check_indices;
    // We batch queries to stay within k=1000 limit. Each pair is 2 indices.
    // 450 pairs = 900 indices.
    for (int i = 2; i <= n; ++i) {
        check_indices.push_back(i);
        check_indices.push_back(1);
        if (check_indices.size() >= 900 || i == n) {
            int res = query(check_indices);
            if (res > 0) s1_is_close = true;
            check_indices.clear();
        }
    }

    char s1_char = s1_is_close ? ')' : '(';
    
    // 2. Prepare pattern for m=6
    int m = 6;
    vector<int> pat_template = find_pattern(m);
    
    // Build decoding map
    map<int, int> decode_map;
    int num_states = 1 << m;
    for (int mask = 0; mask < num_states; ++mask) {
        string s = "";
        for (int x : pat_template) {
            if (x == -1) s += ')';
            else {
                if ((mask >> x) & 1) s += '(';
                else s += ')';
            }
        }
        decode_map[count_rbs(s)] = mask;
    }

    string ans(n, ' ');
    ans[0] = s1_char;

    // 3. Process remaining characters in chunks
    for (int i = 2; i <= n; i += m) {
        int k = min(m, n - i + 1);
        vector<int> chunk_indices;
        for (int j = 0; j < k; ++j) chunk_indices.push_back(i + j);
        // Pad with index 1 if last chunk is smaller than m
        while (chunk_indices.size() < m) chunk_indices.push_back(1);

        vector<int> q;
        if (s1_char == ')') {
            // Filler is ')'. Use pattern directly.
            for (int x : pat_template) {
                if (x == -1) q.push_back(1);
                else q.push_back(chunk_indices[x]);
            }
        } else {
            // Filler is '('. Use reversed pattern logic.
            vector<int> rev_pat = pat_template;
            reverse(rev_pat.begin(), rev_pat.end());
            for (int x : rev_pat) {
                if (x == -1) q.push_back(1);
                else q.push_back(chunk_indices[x]);
            }
        }

        int val = query(q);
        int mask = decode_map[val];
        
        for (int j = 0; j < k; ++j) {
            int bit = (mask >> j) & 1;
            char c;
            if (s1_char == ')') {
                // mask bit 1 -> '('
                c = (bit ? '(' : ')');
            } else {
                // mask bit 1 -> y^swap was '(', so y was ')'
                // mask bit 0 -> y^swap was ')', so y was '('
                c = (bit ? ')' : '(');
            }
            ans[i + j - 1] = c;
        }
    }
    
    cout << "1 " << ans << endl;
}

int main() {
    srand(1337); 
    int n;
    while (cin >> n) {
        solve_case(n);
    }
    return 0;
}