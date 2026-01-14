#include <bits/stdc++.h>
using namespace std;

int main() {
  int b, w, x, y;
  cin >> b >> w >> x >> y;
  if (abs(b - w) <= 1) {
    int total = b + w;
    bool start_black = (b >= w);
    char first = start_black ? '@' : '.';
    char sec = start_black ? '.' : '@';
    string s(total, ' ');
    for (int i = 0; i < total; i++) {
      s[i] = (i % 2 == 0) ? first : sec;
    }
    cout << 1 << " " << total << endl;
    cout << s << endl;
  } else if (b > w + 1) {
    int g = b - w + 1;
    int num_small = w - 1;
    int c_large = 2 * g - 1;
    int total_c = c_large + 2 * num_small;
    vector<string> grid(2, string(total_c, '.'));
    int pos = 0;
    for (int i = 0; i < g; i++) {
      grid[0][pos + 2 * i] = '@';
    }
    pos += c_large;
    for (int sec = 0; sec < num_small; sec++) {
      grid[0][pos] = '@';
      grid[1][pos] = '@';
      pos++;
      pos++;
    }
    cout << 2 << " " << total_c << endl;
    cout << grid[0] << endl;
    cout << grid[1] << endl;
  } else {
    int g = w - b + 1;
    int num_small = b - 1;
    int c_large = 2 * g - 1;
    int total_c = c_large + 2 * num_small;
    vector<string> grid(2, string(total_c, '@'));
    int pos = 0;
    for (int i = 0; i < g; i++) {
      grid[0][pos + 2 * i] = '.';
    }
    pos += c_large;
    for (int sec = 0; sec < num_small; sec++) {
      grid[0][pos] = '.';
      grid[1][pos] = '.';
      pos++;
      pos++;
    }
    cout << 2 << " " << total_c << endl;
    cout << grid[0] << endl;
    cout << grid[1] << endl;
  }
  return 0;
}