#include <bits/stdc++.h>
using namespace std;

string normalize(const string& s) {
    if (s.empty()) return "0";
    size_t start = s.find_first_not_of('0');
    if (start == string::npos) return "0";
    return s.substr(start);
}

bool num_greater(const string& a, const string& b) {
    string aa = normalize(a);
    string bb = normalize(b);
    if (aa.size() != bb.size()) {
        return aa.size() > bb.size();
    }
    return aa > bb;
}

string big_add(string num1, string num2) {
    string result;
    int len1 = num1.size(), len2 = num2.size();
    int carry = 0;
    int i = len1 - 1, j = len2 - 1;
    while (i >= 0 || j >= 0 || carry) {
        int sum = carry;
        if (i >= 0) sum += num1[i--] - '0';
        if (j >= 0) sum += num2[j--] - '0';
        result += (sum % 10) + '0';
        carry = sum / 10;
    }
    reverse(result.begin(), result.end());
    return result;
}

string big_subtract(string num1, string num2) {
    if (num2 == "0") return num1;
    string result;
    int len1 = num1.size(), len2 = num2.size();
    int borrow = 0;
    int i = len1 - 1, j = len2 - 1;
    while (i >= 0 || j >= 0) {
        int sub = borrow;
        if (i >= 0) sub += (num1[i] - '0');
        if (j >= 0) sub -= (num2[j] - '0');
        if (sub < 0) {
            sub += 10;
            borrow = -1;
        } else {
            borrow = 0;
        }
        result += sub + '0';
        if (i >= 0) --i;
        if (j >= 0) --j;
    }
    reverse(result.begin(), result.end());
    size_t startpos = result.find_first_not_of('0');
    if (startpos == string::npos) return "0";
    return result.substr(startpos);
}

int main() {
    int n;
    string W;
    cin >> n >> W;
    vector<string> a(n);
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
    }
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    auto cmp = [&](int i, int j) {
        return num_greater(a[i], a[j]);
    };
    sort(order.begin(), order.end(), cmp);
    string current = "0";
    vector<int> chosen(n, 0);
    string curr_diff = big_subtract(W, current);
    for (int idx : order) {
        string temp = big_add(current, a[idx]);
        bool temp_over = num_greater(temp, W);
        string new_diff = temp_over ? big_subtract(temp, W) : big_subtract(W, temp);
        bool is_better = num_greater(curr_diff, new_diff);
        if (is_better) {
            current = temp;
            chosen[idx] = 1;
            curr_diff = new_diff;
        }
    }
    for (int i = 0; i < n; ++i) {
        cout << chosen[i];
        if (i < n - 1) cout << " ";
        else cout << "\n";
    }
    return 0;
}