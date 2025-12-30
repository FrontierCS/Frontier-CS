#include <bits/stdc++.h>
using namespace std;

static int n;
static long long l1_lim, l2_lim;
static long long qcnt = 0, scnt = 0;

static int ask(int l, int r) {
    cout << 1 << ' ' << l << ' ' << r << '\n';
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    if (x == -1) exit(0);
    ++qcnt;
    return x;
}

static void swp(int i, int j) {
    if (i == j) return;
    cout << 2 << ' ' << i << ' ' << j << '\n';
    cout.flush();
    int ok;
    if (!(cin >> ok)) exit(0);
    if (ok == -1) exit(0);
    ++scnt;
}

static int edges_to_suffix(int k) { // edges between {k} and [k+1..n]
    if (k >= n) return 0;
    int fB = ask(k + 1, n);
    int fU = (k == 1 ? 1 : ask(k, n));
    return 1 + fB - fU;
}

static int edges_to_prefix_of_suffix(int k, int mid) { // edges between {k} and [k+1..mid]
    int fB = ask(k + 1, mid);
    int fU = ask(k, mid);
    return 1 + fB - fU;
}

static int find_first_neighbor_pos(int k) { // assumes there is at least one neighbor in [k+1..n]
    int low = k + 1, high = n;
    while (low < high) {
        int mid = (low + high) >> 1;
        int cnt = edges_to_prefix_of_suffix(k, mid);
        if (cnt >= 1) high = mid;
        else low = mid + 1;
    }
    return low;
}

static void extend_right(int &k) { // path is [1..k], extend at k
    while (k < n) {
        int cnt = edges_to_suffix(k);
        if (cnt == 0) break;
        int pos = find_first_neighbor_pos(k);
        swp(k + 1, pos);
        ++k;
    }
}

static void reverse_prefix(int k) {
    for (int i = 1; i <= k / 2; ++i) swp(i, k + 1 - i);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> l1_lim >> l2_lim)) return 0;

    if (n == 1) {
        cout << 3 << ' ' << 1 << '\n';
        cout.flush();
        return 0;
    }

    int k = 1;
    extend_right(k);
    if (k < n) {
        reverse_prefix(k);
        extend_right(k);
    }

    cout << 3;
    for (int i = 1; i <= n; ++i) cout << ' ' << i;
    cout << '\n';
    cout.flush();
    return 0;
}