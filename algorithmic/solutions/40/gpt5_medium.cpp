#include <bits/stdc++.h>
using namespace std;

int n;

// Send a query with indices seq and read the answer
int ask(const vector<int>& seq) {
    cout << "0 " << seq.size();
    for (int x : seq) cout << " " << x;
    cout << endl;
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    return res;
}

// Build and ask query Q(S,T): concatenate all pairs [a,b] for a in S, b in T
// Return true iff f > 0, meaning exists a in S with '(' and b in T with ')'
bool query_pairs(const vector<int>& S, const vector<int>& T) {
    if (S.empty() || T.empty()) return false;
    // Ensure size constraint: k = 2 * |S| * |T| <= 1000
    long long k = 2LL * S.size() * T.size();
    if (k > 1000) {
        // Should not happen with our usage
        // If it does, split T into smaller parts
        int mid = (int)T.size() / 2;
        vector<int> TL(T.begin(), T.begin() + mid);
        vector<int> TR(T.begin() + mid, T.end());
        return query_pairs(S, TL) || query_pairs(S, TR);
    }
    vector<int> seq;
    seq.reserve((size_t)k);
    for (int a : S) {
        for (int b : T) {
            seq.push_back(a);
            seq.push_back(b);
        }
    }
    int res = ask(seq);
    return res > 0;
}

// Find an index q such that s_q == ')'
int find_any_close_index() {
    int a = 1;
    vector<int> rest;
    for (int i = 2; i <= n; ++i) rest.push_back(i);
    // Split rest into two parts with size up to 500
    vector<int> T1, T2;
    int half = (int)rest.size() / 2;
    T1.assign(rest.begin(), rest.begin() + half);
    T2.assign(rest.begin() + half, rest.end());

    bool r1 = query_pairs(vector<int>{a}, T1);
    bool r2 = query_pairs(vector<int>{a}, T2);

    if (!r1 && !r2) {
        // Then a is ')'
        return a;
    } else {
        // a is '(' and at least one of T1 or T2 contains ')'
        vector<int> T = r1 ? T1 : T2;
        // Binary search within T to find a ')'
        while (T.size() > 1) {
            int mid = (int)T.size() / 2;
            vector<int> L(T.begin(), T.begin() + mid);
            vector<int> R(T.begin() + mid, T.end());
            bool has_in_L = query_pairs(vector<int>{a}, L);
            if (has_in_L) T.swap(L);
            else T.swap(R);
        }
        return T[0];
    }
}

// For a group of indices (size <= 8), query using weights as powers of two
// Block for index i: [i, q, q], repeated weight times
// Returns a vector of chars '(' or ')' for the group
vector<char> classify_group(const vector<int>& group, int q_index) {
    int m = (int)group.size();
    vector<int> seq;
    long long sum_weights = 0;
    for (int r = 0; r < m; ++r) {
        int w = 1 << r;
        sum_weights += w;
    }
    // Ensure k = 3 * sum_weights <= 1000
    // m <= 8 ensures 3*255 = 765 <= 1000
    seq.reserve((size_t)(3 * sum_weights));
    for (int r = 0; r < m; ++r) {
        int idx = group[r];
        int w = 1 << r;
        for (int t = 0; t < w; ++t) {
            seq.push_back(idx);
            seq.push_back(q_index);
            seq.push_back(q_index);
        }
    }
    int res = ask(seq);
    vector<char> ans(m);
    for (int r = 0; r < m; ++r) {
        if (res & 1) ans[r] = '(';
        else ans[r] = ')';
        res >>= 1;
    }
    return ans;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    if (!(cin >> n)) return 0;

    // Find any index q with s_q == ')'
    int q_index = find_any_close_index();

    // Classify all indices in groups of size up to 8
    string s(n, ')'); // default to ')'
    vector<int> all;
    all.reserve(n);
    for (int i = 1; i <= n; ++i) all.push_back(i);

    for (int i = 0; i < n; i += 8) {
        vector<int> group;
        for (int j = i; j < n && j < i + 8; ++j) group.push_back(all[j]);
        vector<char> res = classify_group(group, q_index);
        for (int r = 0; r < (int)group.size(); ++r) {
            s[group[r] - 1] = res[r];
        }
    }

    // Output the final answer
    cout << "1 " << s << endl;
    cout.flush();

    return 0;
}