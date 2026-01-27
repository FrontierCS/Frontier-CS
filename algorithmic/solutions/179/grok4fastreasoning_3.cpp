#include <bits/stdc++.h>
using namespace std;

int cmp(const string& a, const string& b) {
  if (a.size() != b.size()) {
    return a.size() > b.size() ? 1 : -1;
  }
  if (a > b) return 1;
  if (a < b) return -1;
  return 0;
}

string add(const string& a, const string& b) {
  string x = a, y = b;
  if (x.size() < y.size()) swap(x, y);
  string res;
  int carry = 0;
  int i = x.size() - 1;
  int j = y.size() - 1;
  while (i >= 0 || j >= 0 || carry) {
    int sum = carry;
    if (i >= 0) sum += x[i--] - '0';
    if (j >= 0) sum += y[j--] - '0';
    carry = sum / 10;
    res.push_back(sum % 10 + '0');
  }
  reverse(res.begin(), res.end());
  return res;
}

string sub(const string& a, const string& b) {
  string x = a, y = b;
  string res;
  int borrow = 0;
  int i = x.size() - 1;
  int j = y.size() - 1;
  while (i >= 0 || j >= 0 || borrow) {
    int d1 = (i >= 0) ? (x[i--] - '0') : 0;
    int d2 = (j >= 0) ? (y[j--] - '0') : 0;
    int diff = d1 - d2 + borrow;
    if (diff < 0) {
      diff += 10;
      borrow = -1;
    } else {
      borrow = 0;
    }
    res.push_back(diff + '0');
  }
  reverse(res.begin(), res.end());
  size_t start = res.find_first_not_of('0');
  if (start == string::npos) return "0";
  return res.substr(start);
}

string mul2(const string& x) {
  if (x == "0") return "0";
  string res;
  int carry = 0;
  for (int i = x.size() - 1; i >= 0; i--) {
    int d = x[i] - '0';
    int prod = d * 2 + carry;
    carry = prod / 10;
    res = char(prod % 10 + '0') + res;
  }
  if (carry) res = char(carry + '0') + res;
  return res;
}

bool is_zero(const string& s) {
  return s == "0";
}

int main() {
  int n;
  string W_str;
  cin >> n >> W_str;
  vector<string> a(n);
  for (auto& s : a) cin >> s;
  vector<pair<string, int>> items(n);
  for (int i = 0; i < n; i++) {
    items[i] = {a[i], i};
  }
  sort(items.begin(), items.end(), [](const pair<string, int>& p1, const pair<string, int>& p2) {
    return cmp(p1.first, p2.first) > 0;
  });
  vector<int> b(n, 0);
  string S = "0";
  for (auto& item : items) {
    string ai = item.first;
    int idx = item.second;
    if (is_zero(ai)) continue;
    int c = cmp(S, W_str);
    if (c == 0) break;
    if (c > 0) continue;
    string diff = sub(W_str, S);
    string twice = mul2(diff);
    int ca = cmp(ai, twice);
    if (ca < 0) {
      S = add(S, ai);
      b[idx] = 1;
    }
  }
  for (int i = 0; i < n; i++) {
    cout << b[i];
    if (i < n - 1) cout << " ";
    else cout << endl;
  }
  return 0;
}