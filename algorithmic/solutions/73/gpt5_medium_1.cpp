#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int N = n + 3;
    vector<int8_t> inv(N * N, -1);
    vector<int8_t> gt(N * N, -1);

    auto ask = [&](int l, int r) -> int {
        if (l >= r) return 0;
        int idx = l * N + r;
        if (inv[idx] != -1) return inv[idx];
        cout << "0 " << l << " " << r << endl;
        cout.flush();
        int x;
        if (!(cin >> x)) exit(0);
        x &= 1;
        inv[idx] = (int8_t)x;
        return x;
    };

    function<int(int,int)> greater_pair = [&](int i, int j) -> int {
        if (i == j) return 0;
        if (i > j) swap(i, j); // ensure i < j
        int idx = i * N + j;
        if (gt[idx] != -1) return gt[idx];
        int s = 0;
        s ^= ask(i, j);
        s ^= ask(i, j - 1);
        s ^= ask(i + 1, j);
        if (i + 1 < j) s ^= ask(i + 1, j - 1);
        s &= 1;
        gt[idx] = (int8_t)s;
        return s;
    };

    auto less_by_value = [&](int a, int b) -> bool {
        if (a == b) return false;
        if (a < b) return greater_pair(a, b) == 0; // a < b if not (a > b)
        else return greater_pair(b, a) == 1;       // a < b iff b > a
    };

    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 1);
    stable_sort(idx.begin(), idx.end(), less_by_value);

    vector<int> p(n + 1);
    for (int rank = 1; rank <= n; ++rank) {
        int pos = idx[rank - 1];
        p[pos] = rank;
    }

    cout << "1";
    for (int i = 1; i <= n; ++i) cout << " " << p[i];
    cout << endl;
    cout.flush();

    return 0;
}