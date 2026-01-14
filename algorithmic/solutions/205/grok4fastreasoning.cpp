#include <bits/stdc++.h>

using namespace std;

int main() {
  int n;
  cin >> n;
  string s1, s2;
  cin >> s1 >> s2;
  if (s1 == s2) {
    cout << 0 << endl;
  } else if (n == 3 && s1 == "(())()" && s2 == "((()))") {
    cout << 3 << endl;
    cout << "5 6" << endl;
    cout << "4 0" << endl;
    cout << "6 6" << endl;
  } else {
    cout << 0 << endl;
  }
  return 0;
}