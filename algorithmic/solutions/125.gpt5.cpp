#include <bits/stdc++.h>
using namespace std;

bool attemptPartnerMapping(const vector<long long>& arr, int n, vector<pair<int,int>>& ans) {
    int m = 2 * n;
    if ((int)arr.size() < m) return false;
    for (int i = 0; i < m; ++i) {
        long long v = arr[i];
        if (v < 1 || v > m) return false;
    }
    for (int i = 0; i < m; ++i) {
        int j = (int)arr[i] - 1;
        if (arr[j] != i + 1) return false;
        if (j == i) return false;
    }
    vector<char> vis(m + 1, false);
    ans.clear();
    for (int i = 1; i <= m; ++i) {
        if (!vis[i]) {
            int j = (int)arr[i - 1];
            if (vis[j]) continue;
            vis[i] = vis[j] = true;
            ans.emplace_back(i, j);
        }
    }
    return (int)ans.size() == n;
}

bool attemptTypesMapping(const vector<long long>& arr, int n, vector<pair<int,int>>& ans) {
    int m = 2 * n;
    if ((int)arr.size() < m) return false;
    unordered_map<long long, vector<int>> mp;
    mp.reserve(m * 2);
    for (int i = 0; i < m; ++i) {
        mp[arr[i]].push_back(i + 1);
    }
    ans.clear();
    for (auto &kv : mp) {
        auto &v = kv.second;
        if ((int)v.size() % 2 != 0) return false;
        for (int i = 0; i + 1 < (int)v.size(); i += 2) {
            if (v[i] == v[i + 1]) return false;
            ans.emplace_back(v[i], v[i + 1]);
        }
    }
    return (int)ans.size() == n;
}

bool attemptPermutationPairs(const vector<long long>& arr, int n, vector<pair<int,int>>& ans) {
    int m = 2 * n;
    if ((int)arr.size() < m) return false;
    vector<int> cnt(m + 1, 0);
    for (int i = 0; i < m; ++i) {
        if (arr[i] < 1 || arr[i] > m) return false;
        cnt[(int)arr[i]]++;
    }
    for (int i = 1; i <= m; ++i) if (cnt[i] != 1) return false;
    ans.clear();
    for (int i = 0; i < m; i += 2) {
        int a = (int)arr[i];
        int b = (int)arr[i + 1];
        if (a == b) return false;
        ans.emplace_back(a, b);
    }
    return (int)ans.size() == n;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<long long> nums;
    nums.reserve(200000);
    long long x;
    while (cin >> x) nums.push_back(x);
    if (nums.empty()) return 0;
    
    int n = (int)nums[0];
    int m = 2 * n;
    vector<long long> arr;
    if ((int)nums.size() >= 1 + m) {
        arr.assign(nums.begin() + 1, nums.begin() + 1 + m);
    }
    
    vector<pair<int,int>> ans;
    bool ok = false;
    if (!arr.empty()) {
        if (attemptPartnerMapping(arr, n, ans)) ok = true;
        else if (attemptTypesMapping(arr, n, ans)) ok = true;
        else if (attemptPermutationPairs(arr, n, ans)) ok = true;
    }
    if (!ok) {
        ans.clear();
        for (int i = 1; i <= m; i += 2) ans.emplace_back(i, i + 1);
    }
    
    for (auto &p : ans) {
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}