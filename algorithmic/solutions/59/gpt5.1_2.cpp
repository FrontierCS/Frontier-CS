#include <bits/stdc++.h>
using namespace std;

int n;

bool less_than(int i, int j) {
    cout << "? " << i << " " << j << endl;
    cout.flush();
    char c;
    if (!(cin >> c)) exit(0);
    return (c == '<');
}

void merge_sort(vector<int>& a, int l, int r, vector<int>& tmp) {
    if (r - l <= 1) return;
    int m = (l + r) / 2;
    merge_sort(a, l, m, tmp);
    merge_sort(a, m, r, tmp);
    int i = l, j = m, k = l;
    while (i < m && j < r) {
        if (less_than(a[i], a[j])) tmp[k++] = a[i++];
        else tmp[k++] = a[j++];
    }
    while (i < m) tmp[k++] = a[i++];
    while (j < r) tmp[k++] = a[j++];
    for (int t = l; t < r; ++t) a[t] = tmp[t];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    vector<int> idx(n);
    for (int i = 0; i < n; ++i) idx[i] = i + 1;

    vector<int> tmp(n);
    merge_sort(idx, 0, n, tmp);

    vector<int> res(n + 1);
    for (int rank = 1; rank <= n; ++rank) {
        int pos = idx[rank - 1];
        res[pos] = rank;
    }

    cout << "! ";
    for (int i = 1; i <= n; ++i) {
        cout << res[i] << (i == n ? '\n' : ' ');
    }
    cout.flush();

    return 0;
}