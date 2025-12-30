#include <bits/stdc++.h>

using namespace std;

int main() {
  int n;
  cin >> n;
  vector<int> X(n), Y(n);
  vector<long long> R(n);
  for(int i = 0; i < n; i++) {
    cin >> X[i] >> Y[i] >> R[i];
  }
  vector<int> count_col(10000, 0);
  for(int i = 0; i < n; i++) {
    count_col[X[i]]++;
  }
  vector<bool> is_empty(10000, true);
  for(int j = 0; j < 10000; j++) {
    if(count_col[j] > 0) is_empty[j] = false;
  }
  vector<int> order(n);
  iota(order.begin(), order.end(), 0);
  sort(order.begin(), order.end(), [&](int i, int j) {
    if(R[i] != R[j]) return R[i] > R[j];
    return i < j;
  });
  vector<int> AA(n), BB(n), CC(n), DD(n);
  for(int oi = 0; oi < n; oi++) {
    int i = order[oi];
    int px = X[i];
    long long ri = R[i];
    bool do_vertical = (ri > 10000 && count_col[px] == 1);
    if(!do_vertical) {
      long long h = ri;
      int py = Y[i];
      int half = (h - 1LL) / 2;
      long long bbb = (long long)py - half;
      bbb = max(0LL, bbb);
      long long ddd = bbb + h;
      if(ddd > 10000) {
        bbb = 10000 - h;
        ddd = 10000;
      }
      if(bbb > py || ddd < py + 1) {
        bbb = py;
        ddd = py + 1;
      }
      AA[i] = px;
      BB[i] = bbb;
      CC[i] = px + 1;
      DD[i] = ddd;
      continue;
    }
    int left_ext = 0;
    for(int j = px - 1; j >= 0 && is_empty[j]; j--) left_ext++;
    int right_ext = 0;
    for(int j = px + 1; j < 10000 && is_empty[j]; j++) right_ext++;
    int maxw = 1 + left_ext + right_ext;
    double app = (double)ri / 10000.0;
    int w = (int) round(app);
    w = max(1, min(maxw, w));
    int left_take = min(left_ext, (w - 1) / 2);
    int right_take = (w - 1) - left_take;
    right_take = min(right_ext, right_take);
    int curr_w = 1 + left_take + right_take;
    if(curr_w < w) {
      int extra = w - curr_w;
      if(left_ext - left_take > right_ext - right_take) {
        left_take = min(left_ext, left_take + extra);
      } else {
        right_take = min(right_ext, right_take + extra);
      }
      curr_w = 1 + left_take + right_take;
    }
    w = curr_w;
    int startc = px - left_take;
    AA[i] = startc;
    BB[i] = 0;
    CC[i] = startc + w;
    DD[i] = 10000;
    for(int j = startc; j < startc + w; j++) {
      if(j != px) is_empty[j] = false;
    }
  }
  for(int i = 0; i < n; i++) {
    cout << AA[i] << " " << BB[i] << " " << CC[i] << " " << DD[i] << "\n";
  }
  return 0;
}