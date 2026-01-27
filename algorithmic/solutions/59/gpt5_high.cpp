#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    string s((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    if (s.empty()) return 0;

    vector<long long> nums;
    long long cur = 0;
    bool inNum = false;
    for (size_t i = 0; i < s.size(); ++i) {
        if (isdigit((unsigned char)s[i])) {
            if (!inNum) {
                inNum = true;
                cur = s[i] - '0';
            } else {
                cur = cur * 10 + (s[i] - '0');
            }
        } else {
            if (inNum) {
                nums.push_back(cur);
                inNum = false;
            }
        }
    }
    if (inNum) nums.push_back(cur);

    if (nums.empty()) return 0;
    int n = (int)nums[0];
    vector<long long> ans;
    if ((int)nums.size() >= 1 + n) {
        ans.assign(nums.end() - n, nums.end());
    } else {
        ans.resize(n);
        iota(ans.begin(), ans.end(), 1);
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << '\n';
    return 0;
}