#include <bits/stdc++.h>
using namespace std;

bool ask_less(int i, int j) {
    cout << "? " << i << " " << j << endl;
    cout.flush();
    char c;
    if (!(cin >> c)) exit(0);
    return c == '<';
}

void merge_sort(vector<int> &idx, int l, int r, vector<int> &tmp) {
    if (r - l <= 1) return;
    int m = (l + r) / 2;
    merge_sort(idx, l, m, tmp);
    merge_sort(idx, m, r, tmp);
    int i = l, j = m, k = l;
    while (i < m && j < r) {
        if (ask_less(idx[i], idx[j])) tmp[k++] = idx[i++];
        else tmp[k++] = idx[j++];
    }
    while (i < m) tmp[k++] = idx[i++];
    while (j < r) tmp[k++] = idx[j++];
    for (int t = l; t < r; ++t) idx[t] = tmp[t];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> idx(n);
    for (int i = 0; i < n; ++i) idx[i] = i + 1;
    vector<int> tmp(n);

    merge_sort(idx, 0, n, tmp);

    vector<int> ans(n + 1);
    for (int rank = 1; rank <= n; ++rank) {
        int pos = idx[rank - 1];
        ans[pos] = rank;
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << ans[i];
    }
    cout << endl;
    cout.flush();

    return 0;
}