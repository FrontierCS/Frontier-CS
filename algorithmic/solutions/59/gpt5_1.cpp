#include <bits/stdc++.h>
using namespace std;

static inline bool ask_less(int i, int j) {
    cout << "? " << i << " " << j << endl;
    cout.flush();
    char c;
    if (!(cin >> c)) exit(0);
    while (c != '<' && c != '>') {
        if (!(cin >> c)) exit(0);
    }
    return c == '<';
}

static vector<int> merge_two(const vector<int>& A, const vector<int>& B) {
    vector<int> res;
    int i = 0, j = 0;
    int n = (int)A.size(), m = (int)B.size();
    res.reserve(n + m);
    if (n == 0) {
        res.insert(res.end(), B.begin(), B.end());
        return res;
    }
    if (m == 0) {
        res.insert(res.end(), A.begin(), A.end());
        return res;
    }
    // Standard merge with minimal comparisons: stop comparing once one list is exhausted
    while (i < n && j < m) {
        if (ask_less(A[i], B[j])) {
            res.push_back(A[i++]);
        } else {
            res.push_back(B[j++]);
        }
        if (i == n) break;
        if (j == m) break;
    }
    while (i < n) res.push_back(A[i++]);
    while (j < m) res.push_back(B[j++]);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> S[3];
    S[0].reserve((n + 2) / 3);
    S[1].reserve((n + 1) / 3);
    S[2].reserve(n / 3);
    for (int i = 1; i <= n; ++i) {
        S[(i - 1) % 3].push_back(i);
    }

    // Merge two of the three sequences first; choose S0 and S1 (any choice works)
    vector<int> T = merge_two(S[0], S[1]);
    // Then merge with the remaining sequence S2
    vector<int> order = merge_two(T, S[2]);

    vector<int> a(n + 1, 0);
    for (int rank = 1; rank <= (int)order.size(); ++rank) {
        a[order[rank - 1]] = rank;
    }

    cout << "!" ;
    for (int i = 1; i <= n; ++i) cout << " " << a[i];
    cout << endl;
    cout.flush();

    return 0;
}