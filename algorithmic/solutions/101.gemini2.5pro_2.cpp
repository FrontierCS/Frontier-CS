#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>

using namespace std;

int N, R;
vector<pair<int, int>> children;
vector<int> parent;
vector<char> gate_types;
vector<bool> known;

string do_query(const string& s) {
    cout << "? " << s << endl;
    string result;
    cin >> result;
    return result;
}

void force_output(int u, int val, string& s) {
    if (u >= N) {
        s[u] = val + '0';
        return;
    }
    s[u] = '0';
    force_output(children[u].first, val, s);
    force_output(children[u].second, val, s);
}

void solve_gate(int i) {
    if (known[i]) return;

    string s(2 * N + 1, '0');
    
    int curr = i;
    while (curr != 0 && parent[curr] != -1) {
        int p = parent[curr];
        int other_child = (children[p].first == curr) ? children[p].second : children[p].first;
        
        solve_gate(p);

        if (gate_types[p] == '&') {
            force_output(other_child, 1, s);
        } else {
            force_output(other_child, 0, s);
        }
        curr = p;
    }

    force_output(children[i].first, 0, s);
    force_output(children[i].second, 1, s);

    string res = do_query(s);
    if (res == "0") {
        gate_types[i] = '&';
    } else {
        gate_types[i] = '|';
    }
    known[i] = true;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> R;

    children.resize(N);
    parent.assign(2 * N + 1, -1);
    for (int i = 0; i < N; ++i) {
        cin >> children[i].first >> children[i].second;
        parent[children[i].first] = i;
        parent[children[i].second] = i;
    }

    gate_types.assign(N, ' ');
    known.assign(N, false);
    
    if (N > 0) {
        string base_all_0(2 * N + 1, '0');
        string base_all_1_leaves(2 * N + 1, '0');
        for (int i = N; i <= 2 * N; ++i) {
            base_all_1_leaves[i] = '1';
        }

        string res_base0 = do_query(base_all_0);
        string res_base1 = do_query(base_all_1_leaves);

        for (int i = 0; i < R; ++i) {
            string q_str0 = base_all_0;
            q_str0[i] = '1';
            string res0 = do_query(q_str0);
            if (res0 != res_base0) {
                int curr = i;
                while (curr != -1) {
                    gate_types[curr] = '|';
                    known[curr] = true;
                    curr = parent[curr];
                }
            }

            string q_str1 = base_all_1_leaves;
            q_str1[i] = '1';
            string res1 = do_query(q_str1);
            if (res1 != res_base1) {
                 int curr = i;
                 while (curr != -1) {
                    gate_types[curr] = '&';
                    known[curr] = true;
                    curr = parent[curr];
                 }
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        if (!known[i]) {
            solve_gate(i);
        }
    }

    cout << "! ";
    for (int i = 0; i < N; ++i) {
        cout << gate_types[i];
    }
    cout << endl;

    return 0;
}