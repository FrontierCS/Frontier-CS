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
        result += (sum % 10) + '0';
        carry = sum / 10;
    }
    reverse(result.begin(), result.end());
    return result;
}

bool leq(const string& num1, const string& num2) {
    if (num1.size() != num2.size()) {
        return num1.size() < num2.size();
    }
    return num1 <= num2;
}

bool greater_str(const string& x, const string& y) {
    if (x.size() != y.size()) {
        return x.size() > y.size();
    }
    return x > y;
}

int main() {
    int n;
    string w;
    cin >> n >> w;
    vector<string> a(n);
    for (int i = 0; i < n; i++) {
        cin >> a[i];
    }
    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);
    sort(idx.begin(), idx.end(), [&](int i, int j) {
        return greater_str(a[i], a[j]);
    });
    string current = "0";
    vector<int> b(n, 0);
    for (int pos : idx) {
        string candidate = add(current, a[pos]);
        if (leq(candidate, w)) {
            current = candidate;
            b[pos] = 1;
        }
    }
    for (int i = 0; i < n; i++) {
        if (i > 0) cout << " ";
        cout << b[i];
    }
    cout << endl;
    return 0;
}