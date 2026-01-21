#include <bits/stdc++.h>
using namespace std;

struct Interactor {
    int n;
    long long qcnt = 0;
    long long qlim = (long long)5 * 30000 / 3 + 5;
    unordered_map<unsigned long long, bool> memo;
    bool interactive = true;

    static unsigned long long key(int a, int b) {
        if (a > b) swap(a, b);
        return (unsigned long long)(unsigned int)a << 32 | (unsigned int)b;
    }

    bool askLess(int i, int j) {
        if (i == j) return false;
        unsigned long long k = key(i, j);
        auto it = memo.find(k);
        if (it != memo.end()) {
            bool ans = it->second;
            return (i < j) ? ans : !ans;
        }

        if (!interactive) {
            bool ans = i < j;
            memo.emplace(k, ans);
            return ans;
        }

        ++qcnt;
        cout << "? " << i << " " << j << endl;

        string s;
        if (!(cin >> s)) {
            interactive = false;
            bool ans = i < j;
            memo.emplace(k, ans);
            return ans;
        }
        while (s.size() == 0) {
            if (!(cin >> s)) {
                interactive = false;
                bool ans = i < j;
                memo.emplace(k, ans);
                return ans;
            }
        }
        char c = s[0];
        bool ans_ij = (c == '<');
        memo.emplace(k, ans_ij);
        return (i < j) ? ans_ij : !ans_ij;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Interactor it;
    if (!(cin >> it.n)) return 0;
    int n = it.n;
    it.qlim = (long long)5 * n / 3 + 5;

    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 1);

    auto cmp = [&](int i, int j) -> bool {
        return it.askLess(i, j);
    };

    // If not interactive (e.g., local run), just output identity.
    // Otherwise, attempt to sort indices by value using comparisons.
    stable_sort(idx.begin(), idx.end(), cmp);

    vector<int> a(n + 1);
    for (int r = 1; r <= n; r++) {
        a[idx[r - 1]] = r;
    }

    cout << "!";
    for (int i = 1; i <= n; i++) cout << " " << a[i];
    cout << endl;
    return 0;
}