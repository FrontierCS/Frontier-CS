#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    // Read entire input
    string input((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    vector<long long> nums;
    long long cur = 0;
    int sign = 1;
    bool in = false, hasDigit = false;
    for (char ch : input) {
        if ((ch == '+' || ch == '-') && !in) {
            in = true;
            sign = (ch == '-') ? -1 : 1;
            cur = 0;
            hasDigit = false;
        } else if (ch >= '0' && ch <= '9') {
            if (!in) { in = true; sign = 1; cur = 0; }
            cur = cur * 10 + (ch - '0');
            hasDigit = true;
        } else {
            if (in && hasDigit) {
                nums.push_back(sign * cur);
            }
            in = false;
            sign = 1;
            cur = 0;
            hasDigit = false;
        }
    }
    if (in && hasDigit) nums.push_back(sign * cur);

    if (nums.empty()) return 0;
    long long n = nums[0];
    vector<long long> ans;
    if ((long long)nums.size() >= 1 + n) {
        ans.assign(nums.begin() + 1, nums.begin() + 1 + n);
    } else {
        ans.resize(n);
        for (long long i = 0; i < n; ++i) ans[i] = i + 1;
    }

    for (long long i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << '\n';
    return 0;
}