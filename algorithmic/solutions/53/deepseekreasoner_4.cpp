#include <bits/stdc++.h>
using namespace std;

int n;
int k;

int ask(const vector<int>& q) {
    cout << "?";
    for (int x : q) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

void answer(const vector<int>& p) {
    cout << "!";
    for (int x : p) cout << " " << x;
    cout << endl;
}

// returns the difference D for pair (a,b) and also stores the sum of two answers in sum_ret
int query_pair(int a, int b, int& sum_ret) {
    // choose first element that is neither a nor b
    int first_elem = n;
    while (first_elem == a || first_elem == b) first_elem--;

    vector<int> rest;
    for (int i = 1; i <= n; i++) {
        if (i != a && i != b && i != first_elem) {
            rest.push_back(i);
        }
    }
    sort(rest.begin(), rest.end());

    vector<int> q1 = {first_elem, a, b};
    q1.insert(q1.end(), rest.begin(), rest.end());
    int ans1 = ask(q1);

    vector<int> q2 = {first_elem, b, a};
    q2.insert(q2.end(), rest.begin(), rest.end());
    int ans2 = ask(q2);

    sum_ret = ans1 + ans2;
    return ans1 - ans2;
}

void solve() {
    cin >> n;
    // choose k = 1
    k = 1;
    cout << k << endl;

    vector<int> p(n + 1, 0);
    vector<bool> used(n + 1, false);

    for (int start = 1; start <= n; start++) {
        if (used[start]) continue;

        vector<int> cycle;
        int cur = start;
        while (true) {
            int best = -1;
            int best_sum = -1;
            bool found = false;

            for (int nxt = 1; nxt <= n; nxt++) {
                if (nxt == cur || used[nxt]) continue;
                int sum_val;
                int d = query_pair(cur, nxt, sum_val);
                if (d == 1) {
                    p[cur] = nxt;
                    used[cur] = true;
                    cur = nxt;
                    found = true;
                    break;
                }
                if (sum_val > best_sum) {
                    best_sum = sum_val;
                    best = nxt;
                }
            }

            if (found) continue;

            // 2‑cycle case
            p[cur] = best;
            p[best] = cur;
            used[cur] = used[best] = true;
            break;
        }
    }

    vector<int> res(n);
    for (int i = 1; i <= n; i++) {
        res[i - 1] = p[i];
    }
    answer(res);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}