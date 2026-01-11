#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<long double> nums;
    string s;
    while (cin >> s) {
        char* endptr = nullptr;
        long double val = strtold(s.c_str(), &endptr);
        if (endptr != s.c_str() && *endptr == '\0') {
            nums.push_back(val);
        }
    }

    if (nums.empty()) return 0;

    auto is_integer = [](long double x) {
        long double r = llround(x);
        return fabsl(x - r) < 1e-9L;
    };

    vector<array<long long,3>> cases;

    if (nums.size() >= 4 && is_integer(nums[0])) {
        long long T = llround(nums[0]);
        if (nums.size() == 1 + 3ULL * T) {
            for (long long i = 0; i < T; ++i) {
                long long x = llround(nums[1 + 3*i + 0]);
                long long y = llround(nums[1 + 3*i + 1]);
                long long r = llround(nums[1 + 3*i + 2]);
                cases.push_back({x,y,r});
            }
        } else if (nums.size() % 3 == 0) {
            for (size_t i = 0; i < nums.size(); i += 3) {
                long long x = llround(nums[i+0]);
                long long y = llround(nums[i+1]);
                long long r = llround(nums[i+2]);
                cases.push_back({x,y,r});
            }
        } else if (nums.size() >= 3) {
            long long x = llround(nums[0]);
            long long y = llround(nums[1]);
            long long r = llround(nums[2]);
            cases.push_back({x,y,r});
        }
    } else if (nums.size() % 3 == 0) {
        for (size_t i = 0; i < nums.size(); i += 3) {
            long long x = llround(nums[i+0]);
            long long y = llround(nums[i+1]);
            long long r = llround(nums[i+2]);
            cases.push_back({x,y,r});
        }
    } else if (nums.size() >= 3) {
        long long x = llround(nums[0]);
        long long y = llround(nums[1]);
        long long r = llround(nums[2]);
        cases.push_back({x,y,r});
    }

    for (auto &c : cases) {
        cout << "answer " << c[0] << ' ' << c[1] << ' ' << c[2] << "\n";
    }

    return 0;
}