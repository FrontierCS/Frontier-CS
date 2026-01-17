#include <bits/stdc++.h>
using namespace std;

int n;
vector<vector<int>> memo;

int query(int l, int r) {
    cout << "0 " << l << ' ' << r << endl;
    int res;
    cin >> res;
    return res;
}

int getInv(int l, int r) {
    if (l == r) return 0;
    if (memo[l][r] != -1) return memo[l][r];
    int res = query(l, r);
    memo[l][r] = res;
    return res;
}

bool isGreater(int i, int j) {
    if (i == j) return false;
    if (i < j) {
        int comp = getInv(i, j);
        if (j - 1 >= i) comp ^= getInv(i, j - 1);
        if (i + 1 <= j) comp ^= getInv(i + 1, j);
        if (i + 1 <= j - 1) comp ^= getInv(i + 1, j - 1);
        return comp == 1;
    } else {
        // i > j
        int comp = getInv(j, i);
        if (i - 1 >= j) comp ^= getInv(j, i - 1);
        if (j + 1 <= i) comp ^= getInv(j + 1, i);
        if (j + 1 <= i - 1) comp ^= getInv(j + 1, i - 1);
        return comp == 0;
    }
}

vector<int> mergeSort(const vector<int>& v) {
    int sz = v.size();
    if (sz <= 1) return v;
    int mid = sz / 2;
    vector<int> left(v.begin(), v.begin() + mid);
    vector<int> right(v.begin() + mid, v.end());
    left = mergeSort(left);
    right = mergeSort(right);
    vector<int> merged;
    int i = 0, j = 0;
    while (i < left.size() && j < right.size()) {
        if (!isGreater(left[i], right[j])) {
            merged.push_back(left[i]);
            i++;
        } else {
            merged.push_back(right[j]);
            j++;
        }
    }
    while (i < left.size()) merged.push_back(left[i++]);
    while (j < right.size()) merged.push_back(right[j++]);
    return merged;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> n;
    memo.assign(n + 1, vector<int>(n + 1, -1));
    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 1);
    vector<int> sorted = mergeSort(idx);
    vector<int> p(n + 1);
    for (int i = 0; i < n; ++i) {
        p[sorted[i]] = i + 1;
    }
    cout << "1";
    for (int i = 1; i <= n; ++i) {
        cout << ' ' << p[i];
    }
    cout << endl;
    return 0;
}