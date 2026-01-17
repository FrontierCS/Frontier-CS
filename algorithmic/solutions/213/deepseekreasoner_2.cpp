#include <bits/stdc++.h>
using namespace std;

int n, x;
vector<int> a;
vector<int> pos; // position of each value
vector<tuple<int, int, int>> ops; // (l, r, dir)

void rotate(int l, int dir) {
    int r = l + x - 1;
    if (dir == 0) { // left shift
        int tmp = a[l];
        for (int i = l; i < r; ++i) a[i] = a[i + 1];
        a[r] = tmp;
    } else { // right shift
        int tmp = a[r];
        for (int i = r; i > l; --i) a[i] = a[i - 1];
        a[l] = tmp;
    }
    // update positions
    for (int i = l; i <= r; ++i) pos[a[i]] = i;
    ops.push_back({l, r, dir});
}

void move_value(int v, int target) {
    while (pos[v] != target) {
        int p = pos[v];
        if (p > target) { // need to move left
            int d = p - target;
            if (d >= x - 1) {
                int s = p - x + 1; // s >= target because d >= x-1
                rotate(s, 1); // right rotate -> v moves to s
            } else {
                // fine move left
                if (target + x - 1 <= n) {
                    rotate(target, 0); // left rotate on [target, target+x-1]
                } else {
                    // target in the last x-1 positions
                    rotate(n - x + 1, 0); // left rotate on [n-x+1, n]
                }
            }
        } else { // p < target, need to move right
            int d = target - p;
            if (d >= x - 1) {
                int s = p; // window [p, p+x-1]
                rotate(s, 0); // left rotate -> v moves to p+x-1
            } else {
                // fine move right
                if (p + x - 1 <= n) {
                    rotate(p, 1); // right rotate on [p, p+x-1]
                } else {
                    // p in the last x-1 positions
                    rotate(n - x + 1, 1); // right rotate on [n-x+1, n]
                }
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> n;
    a.resize(n + 1);
    pos.resize(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        pos[a[i]] = i;
    }

    // choose x
    if (n