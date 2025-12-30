#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <iomanip>
#include <algorithm>

using namespace std;

// Returns true if s1 is "more general" than s2, i.e., M(s2) is a subset of M(s1).
// This implies s1 can represent every string s2 can.
// Condition: for every pos k, s1[k] == '?' or s1[k] == s2[k].
// Note: If s1[k] is a character, s2[k] must be the same character (it cannot be '?',
// because if s2[k] was '?', s2 could match a char that s1 doesn't).
bool covers(const string& s1, const string& s2) {
    int n = s1.length();
    for (int i = 0; i < n; ++i) {
        if (s1[i] == '?') continue;
        if (s1[i] != s2[i]) return false;
    }
    return true;
}

// Compute intersection pattern of s1 and s2.
// Returns {true, pattern} if intersection is non-empty, {false, ""} otherwise.
pair<bool, string> intersect_patterns(const string& s1, const string& s2) {
    int n = s1.length();
    string res(n, ' ');
    for (int i = 0; i < n; ++i) {
        if (s1[i] == '?' && s2[i] == '?') {
            res[i] = '?';
        } else if (s1[i] == '?') {
            res[i] = s2[i];
        } else if (s2[i] == '?') {
            res[i] = s1[i];
        } else {
            if (s1[i] != s2[i]) return {false, ""};
            res[i] = s1[i];
        }
    }
    return {true, res};
}

int count_wildcards(const string& s) {
    int cnt = 0;
    for (char c : s) if (c == '?') cnt++;
    return cnt;
}

int N, M;
vector<string> patterns;
vector<vector<int>> adj;
vector<int> component;
vector<bool> vis;
long double comp_prob;

void get_component_nodes(int u) {
    vis[u] = true;
    component.push_back(u);
    for (int v : adj[u]) {
        if (!vis[v]) get_component_nodes(v);
    }
}

// Principle of Inclusion-Exclusion DFS
// current_s: the intersection of the currently selected subset of patterns
// cnt_patterns: size of the subset
void solve_pie(int idx_in_comp, const string& current_s, int cnt_patterns) {
    int k = count_wildcards(current_s);
    // The number of valid DNA strings matching current_s is 4^k.
    // The probability is 4^k / 4^N = (1/4)^(N-k).
    // Sign is (-1)^(cnt_patterns - 1).
    long double p = pow((long double)0.25, N - k);
    if (cnt_patterns % 2 == 1) comp_prob += p;
    else comp_prob -= p;

    // Try adding more patterns from the component to the subset
    for (int i = idx_in_comp + 1; i < component.size(); ++i) {
        int next_idx = component[i];
        pair<bool, string> res = intersect_patterns(current_s, patterns[next_idx]);
        if (res.first) {
            solve_pie(i, res.second, cnt_patterns + 1);
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;

    vector<string> raw_patterns(M);
    for (int i = 0; i < M; ++i) {
        cin >> raw_patterns[i];
    }

    // 1. Remove redundant patterns
    // If pattern A covers pattern B (M(B) subset of M(A)), then M(A) U M(B) = M(A).
    // We can discard B.
    vector<bool> active(M, true);
    for (int i = 0; i < M; ++i) {
        if (!active[i]) continue;
        for (int j = 0; j < M; ++j) {
            if (i == j) continue;
            if (!active[j]) continue;
            if (covers(raw_patterns[i], raw_patterns[j])) {
                active[j] = false;
            }
        }
    }

    patterns.clear();
    for (int i = 0; i < M; ++i) {
        if (active[i]) patterns.push_back(raw_patterns[i]);
    }
    
    M = patterns.size();
    if (M == 0) {
        cout << "0.000000" << endl;
        return 0;
    }

    // 2. Build compatibility graph
    // Two patterns are compatible if they have a non-empty intersection.
    adj.assign(M, vector<int>());
    for (int i = 0; i < M; ++i) {
        for (int j = i + 1; j < M; ++j) {
            pair<bool, string> res = intersect_patterns(patterns[i], patterns[j]);
            if (res.first) {
                adj[i].push_back(j);
                adj[j].push_back(i);
            }
        }
    }

    // 3. Process each connected component
    // Sets of strings matched by different components are disjoint because
    // patterns from different components are incompatible.
    // Thus we can sum the probabilities of the union of each component.
    vis.assign(M, false);
    long double total_prob = 0;

    for (int i = 0; i < M; ++i) {
        if (!vis[i]) {
            component.clear();
            get_component_nodes(i);
            
            comp_prob = 0;
            // Run PIE on this component
            for (int k = 0; k < component.size(); ++k) {
                solve_pie(k, patterns[component[k]], 1);
            }
            total_prob += comp_prob;
        }
    }

    cout << fixed << setprecision(10) << total_prob << endl;

    return 0;
}