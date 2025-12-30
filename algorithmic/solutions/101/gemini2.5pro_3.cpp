#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>

using namespace std;

int N, R;
vector<pair<int, int>> connections;
string current_guess_str;
vector<int> p_outputs;

void get_outputs(const string& s, int start_node) {
    for (int i = start_node; i >= 0; --i) {
        if (i >= N) {
            p_outputs[i] = s[i] - '0';
        } else {
            int u = connections[i].first;
            int v = connections[i].second;
            int slot_out;
            if (current_guess_str[i] == '&') {
                slot_out = p_outputs[u] & p_outputs[v];
            } else {
                slot_out = p_outputs[u] | p_outputs[v];
            }
            p_outputs[i] = slot_out ^ (s[i] - '0');
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> R;
    connections.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> connections[i].first >> connections[i].second;
    }

    vector<string> test_queries(R, string(2 * N + 1, '0'));
    vector<int> true_outputs(R);

    for (int i = 0; i < R; ++i) {
        test_queries[i][N + i] = '1';
        cout << "? " << test_queries[i] << endl;
        cin >> true_outputs[i];
    }
    
    current_guess_str.assign(N, '&');
    p_outputs.resize(2 * N + 1);

    vector<int> p_outputs_or(R);
    vector<int> p_outputs_and(R);

    for (int i = N - 1; i >= 0; --i) {
        // Pre-calculate outputs for nodes > i, which are fixed for this iteration
        for (int k = 0; k < R; ++k) {
            get_outputs(test_queries[k], 2 * N);
            p_outputs_and[k] = p_outputs[0];
        }

        current_guess_str[i] = '|';
        bool or_matches = true;
        for (int k = 0; k < R; ++k) {
            get_outputs(test_queries[k], i);
            if (p_outputs[0] != true_outputs[k]) {
                or_matches = false;
                break;
            }
        }
        
        if (or_matches) {
            // Keep it as '|'
        } else {
            current_guess_str[i] = '&';
        }
    }
    
    cout << "! " << current_guess_str << endl;

    return 0;
}