#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

int N, R;
vector<pair<int, int>> connections;
vector<int> parent;
vector<char> gate_type;

// A helper to merge two partial query strings.
// '?' means unset. '0' or '1' is set.
string merge(string s1, const string& s2) {
    for (size_t i = 0; i < s1.length(); ++i) {
        if (s1[i] == '?' && s2[i] != '?') {
            s1[i] = s2[i];
        } else if (s1[i] != '?' && s2[i] != '?' && s1[i] != s2[i]) {
            // This should not happen in this problem due to tree structure
            // but is good practice for robustness.
            return ""; 
        }
    }
    return s1;
}

// force now returns a partial string to be merged
string force(int j, int v) {
    string s(2 * N + 1, '?');
    if (j >= N) {
        s[j] = v + '0';
    } else {
        string s_u = force(connections[j].first, v);
        string s_v = force(connections[j].second, v);
        
        string merged_uv = merge(s_u, s_v);

        s = merged_uv;
        s[j] = '0';
    }
    return s;
}

int do_query(string& s) {
    for (char& c : s) {
        if (c == '?') {
            c = '0';
        }
    }
    cout << "? " << s << endl;
    int result;
    cin >> result;
    return result;
}

void answer(const string& t) {
    cout << "! " << t << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> R;
    connections.resize(N);
    parent.assign(2 * N + 1, -1);

    for (int i = 0; i < N; ++i) {
        int u, v;
        cin >> u >> v;
        connections[i] = {u, v};
        parent[u] = i;
        parent[v] = i;
    }
    
    gate_type.resize(N);

    for (int i = 0; i < N; ++i) {
        string s_base_partial = force(connections[i].first, 0);
        s_base_partial = merge(s_base_partial, force(connections[i].second, 0));

        string s_test_partial = force(connections[i].first, 0);
        s_test_partial = merge(s_test_partial, force(connections[i].second, 1));

        vector<int> path_to_root;
        int curr = i;
        while(curr != -1) {
            path_to_root.push_back(curr);
            curr = parent[curr];
        }
        reverse(path_to_root.begin(), path_to_root.end());
        // path_to_root is now [0, parent_of_child, ..., parent_of_i, i]
        
        for(size_t j = 0; j < path_to_root.size() - 1; ++j) {
            int p = path_to_root[j];
            int child = path_to_root[j+1];
            int sibling = (connections[p].first == child) ? connections[p].second : connections[p].first;
            
            string s_sibling_partial;
            if (gate_type[p] == '&') {
                s_sibling_partial = force(sibling, 1);
            } else { // OR (or unknown, treat as OR - default)
                s_sibling_partial = force(sibling, 0);
            }
            s_base_partial = merge(s_base_partial, s_sibling_partial);
            s_test_partial = merge(s_test_partial, s_sibling_partial);
        }
        
        int out_base = do_query(s_base_partial);
        int out_test = do_query(s_test_partial);

        if (out_base != out_test) {
            gate_type[i] = '|';
        } else {
            gate_type[i] = '&';
        }
    }

    string result_t = "";
    for(int i = 0; i < N; ++i) result_t += gate_type[i];
    answer(result_t);

    return 0;
}