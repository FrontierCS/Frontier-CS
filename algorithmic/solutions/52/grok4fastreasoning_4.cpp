#include <bits/stdc++.h>
using namespace std;

int main() {
  int n, l1, l2;
  cin >> n >> l1 >> l2;
  vector<bool> connected(n);
  for(int i = 1; i < n; i++) {
    cout << "1 " << i << " " << (i + 1) << endl;
    cout.flush();
    int x;
    cin >> x;
    connected[i] = (x == 1);
  }
  vector<int> run_start, run_len;
  int cur = 1;
  for(int i = 1; i < n; i++) {
    if(!connected[i]) {
      run_len.push_back(i - cur + 1);
      run_start.push_back(cur);
      cur = i + 1;
    }
  }
  run_len.push_back(n - cur + 1);
  run_start.push_back(cur);
  int cc = run_len.size();
  vector<int> value_order;
  for(int i = 2; i <= cc; i += 2) value_order.push_back(i);
  for(int i = 1; i <= cc; i += 2) value_order.push_back(i);
  vector<int> low_run(cc);
  int curval = 1;
  for(int k = 0; k < cc; k++) {
    int ch = value_order[k] - 1;
    low_run[ch] = curval;
    curval += run_len[ch];
  }
  vector<bool> dec(cc, true);
  for(int r = 1; r < cc; r++) {
    int pr = r - 1;
    int plo = low_run[pr];
    int ple = run_len[pr];
    int phi = plo + ple - 1;
    bool pdec = dec[pr];
    int prev_right = pdec ? plo : phi;
    int clo = low_run[r];
    int cle = run_len[r];
    int chi = clo + cle - 1;
    int left_dec = chi;
    int left_inc = clo;
    bool bad_dec = (abs(prev_right - left_dec) == 1);
    bool bad_inc = (abs(prev_right - left_inc) == 1);
    if(!bad_dec) {
      dec[r] = true;
    } else if(!bad_inc) {
      dec[r] = false;
    } else {
      int new_prev_right = pdec ? phi : plo;
      bool nbad_dec = (abs(new_prev_right - left_dec) == 1);
      bool nbad_inc = (abs(new_prev_right - left_inc) == 1);
      if(!nbad_dec || !nbad_inc) {
        dec[r] = nbad_dec ? false : true;
        dec[pr] = !dec[pr];
      } else {
        dec[r] = true;
      }
    }
  }
  vector<int> pp(n + 1);
  for(int r = 0; r < cc; r++) {
    int st = run_start[r];
    int le = run_len[r];
    int lo = low_run[r];
    int hi = lo + le - 1;
    if(dec[r]) {
      for(int k = 0; k < le; k++) {
        pp[st + k] = hi - k;
      }
    } else {
      for(int k = 0; k < le; k++) {
        pp[st + k] = lo + k;
      }
    }
  }
  cout << "3";
  for(int i = 1; i <= n; i++) {
    cout << " " << pp[i];
  }
  cout << endl;
  cout.flush();
  return 0;
}