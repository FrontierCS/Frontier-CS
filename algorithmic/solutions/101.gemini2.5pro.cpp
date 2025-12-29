#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

int N, R;
vector<pair<int, int>> connections;

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

int query(const string& s) {
    cout << "? " << s << endl;
    int result;
    cin >> result;
    return result;
}

void answer(const string& t) {
    cout << "! " << t << endl;
}

// Sets switches in the subtree of node j to make its output become v.
// This works regardless of the gate types in the subtree.
void force_output(int j, int v, string& s) {
    if (j >= N) {
        s[j] = v + '0';
        return;
    }
    // For an internal node j, to make its output v, we can set its switch S[j] to 0,
    // and make its gate's output become v. This is achieved by setting its inputs
    // to (v,v), which yields v for both AND and OR gates.
    s[j] = '0';
    force_output(connections[j].first, v, s);
    force_output(connections[j].second, v, s);
}

string random_string(int len) {
    string s(len, '0');
    uniform_int_distribution<int> dist(0, 1);
    for (int i = 0; i < len; ++i) {
        s[i] = dist(rng) + '0';
    }
    return s;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> R;
    connections.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> connections[i].first >> connections[i].second;
    }

    string gate_types_str(N, '&');
    vector<string> sensitizing_strings(N);
    
    vector<int> p(N);
    iota(p.begin(), p.end(), 0);
    shuffle(p.begin(), p.end(), rng);
    
    int queries_left = 4990;

    // Determine a budget for finding sensitizing strings.
    // The total queries should be minimized. With N gates, we need at least 2N queries for testing.
    // The rest can be used for finding sensitizing strings. Each attempt costs 2 queries.
    int attempts_per_node = 0;
    if (N > 0) {
        // A simple heuristic for query budget. Aim for under 900 for full score.
        // If N is large, we can't afford many attempts.
        if (N <= 200) {
           attempts_per_node = (900 - 2*N) / (2*N);
        } else {
           attempts_per_node = (4990 - 2*N) / (2*N);
        }
    }
    attempts_per_node = max(1, attempts_per_node);

    // Phase 1: Find a sensitizing string for each gate i.
    // A string s is sensitizing for i if flipping switch S[i] flips the circuit output.
    for (int i : p) {
        if (queries_left < 2 * attempts_per_node) break;
        for (int k = 0; k < attempts_per_node; ++k) {
            string s = random_string(2 * N + 1);
            int q1 = query(s);
            s[i] = (s[i] == '0' ? '1' : '0');
            int q2 = query(s);
            queries_left -= 2;
            if (q1 != q2) {
                s[i] = (s[i] == '0' ? '1' : '0'); // flip back
                sensitizing_strings[i] = s;
                break;
            }
        }
    }

    // Phase 2: Test each gate for which a sensitizing string was found.
    // We test the gate's response to inputs (0,0) vs (0,1).
    // An OR gate will output 0 then 1, an AND gate will output 0 then 0.
    // If the path is sensitized, this difference will propagate to the final output.
    for (int i = 0; i < N; ++i) {
        if (!sensitizing_strings[i].empty() && queries_left >= 2) {
            string s = sensitizing_strings[i];

            // Test with inputs (0,0) to gate i
            string s_test_00 = s;
            force_output(connections[i].first, 0, s_test_00);
            force_output(connections[i].second, 0, s_test_00);
            int out00 = query(s_test_00);

            // Test with inputs (0,1) to gate i
            string s_test_01 = s;
            force_output(connections[i].first, 0, s_test_01);
            force_output(connections[i].second, 1, s_test_01);
            int out01 = query(s_test_01);
            queries_left -= 2;
            
            if (out00 != out01) {
                gate_types_str[i] = '|';
            }
        }
    }

    answer(gate_types_str);

    return 0;
}