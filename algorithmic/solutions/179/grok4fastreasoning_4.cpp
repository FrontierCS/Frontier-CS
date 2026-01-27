#include <bits/stdc++.h>
using namespace std;

string add(string num1, string num2) {
    string result;
    int len1 = num1.size();
    int len2 = num2.size();
    int carry = 0;
    int i = len1 - 1;
    int j = len2 - 1;
    while (i >= 0 || j >= 0 || carry) {
        int sum = carry;
        if (i >= 0) sum += num1[i--] - '0';
        if (j >= 0) sum += num2[j--] - '0';
        result.push_back(sum % 10 + '0');
        carry = sum / 10;
    }
    reverse(result.begin(), result.end());
    if (result.empty()) return "0";
    return result;
}

int compare(const string& num1, const string& num2) {
    if (num1.size() > num2.size()) return 1;
    if (num1.size() < num2.size()) return -1;
    if (num1 > num2) return 1;
    if (num1 < num2) return -1;
    return 0;
}

int main() {
    int n;
    string W_str;
    cin >> n >> W_str;
    vector<pair<string, int>> items;
    for (int i = 0; i < n; i++) {
        string s;
        cin >> s;
        items.emplace_back(s, i);
    }
    auto cmp = [](const pair<string, int>& x, const pair<string, int>& y) {
        const string& a = x.first;
        const string& b = y.first;
        if (a.size() != b.size()) return a.size() > b.size();
        return a > b;
    };
    sort(items.begin(), items.end(), cmp);
    string current = "0";
    vector<int> choice(n, 0);
    for (auto& p : items) {
        string candidate = add(current, p.first);
        if (compare(candidate, W_str) <= 0) {
            current = candidate;
            choice[p.second] = 1;
        }
    }
    for (int i = 0; i < n; i++) {
        if (i > 0) cout << " ";
        cout << choice[i];
    }
    cout << endl;
    return 0;
}