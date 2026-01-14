#include <bits/stdc++.h>
using namespace std;

int main() {
  long long k;
  cin >> k;
  if (k == 1) {
    cout << 1 << endl;
    cout << "HALT PUSH 1 GOTO 1" << endl;
    return 0;
  }
  long long m = (k - 1) / 2;
  if (k <= 513) {
    // linear
    if (m == 1) {
      cout << 3 << endl;
      cout << "POP 2 GOTO 1 PUSH 1 GOTO 2" << endl;
      cout << "POP 1 GOTO 3 PUSH 2 GOTO 3" << endl;
      cout << "HALT PUSH 1 GOTO 3" << endl;
    } else {
      int n = 2 * m;
      cout << n << endl;
      int wrong = 2, b = 1;
      int halt_pos = m;
      // push phase 1 to m
      for (int i = 1; i <= m; i++) {
        if (i == m) {
          cout << "HALT PUSH " << b << " GOTO " << (m + 1) << endl;
        } else {
          cout << "POP " << wrong << " GOTO " << i << " PUSH " << b << " GOTO " << (i + 1) << endl;
        }
      }
      // pop phase m+1 to 2m
      for (int j = 1; j <= m; j++) {
        int pos = m + j;
        int next_pos = (j < m ? m + j + 1 : halt_pos);
        cout << "POP " << b << " GOTO " << next_pos << " PUSH " << wrong << " GOTO " << pos << endl;
      }
    }
    return 0;
  }
  // binary
  vector<int> zero_sym(31), one_sym(31);
  for (int i = 0; i < 31; i++) {
    zero_sym[i] = 2 * i + 1;
    one_sym[i] = 2 * i + 2;
  }
  int temp_sym = 1024;
  int wrong_a = 1023;
  int added_b = 64;
  // binary search mm
  long long low = 0, high = (1LL << 31) - 1;
  long long best_mm = 0;
  while (low <= high) {
    long long mid = low + (high - low) / 2;
    long long sumt = 0;
    for (int kk = 1; kk <= 31; kk++) {
      sumt += (mid >> kk);
    }
    long long gg = 31LL + 4 * sumt + 4 * mid + 124LL + 31LL;
    if (gg <= k - 1) {
      best_mm = mid;
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }
  long long mm = best_mm;
  // bits
  vector<int> bit_val(31);
  for (int i = 0; i < 31; i++) {
    bit_val[i] = ((mm & (1LL << i)) ? one_sym[i] : zero_sym[i]);
  }
  // compute g
  long long sumt = 0;
  for (int kk = 1; kk <= 31; kk++) {
    sumt += (mm >> kk);
  }
  long long g = 31LL + 4 * sumt + 4 * mm + 124LL + 31LL;
  long long ee = k - g - 1;
  int l = ee / 2;
  // positions
  int pos = 1;
  vector<int> setup_pos(31);
  for (int i = 0; i < 31; i++) setup_pos[i] = pos++;
  vector<int> a_pos(31), b_pos(31), c_pos(31);
  for (int i = 0; i < 31; i++) {
    a_pos[i] = pos++;
    b_pos[i] = pos++;
    c_pos[i] = pos++;
  }
  vector<int> p1_pos(30);
  for (int i = 0; i < 30; i++) p1_pos[i] = pos++;
  vector<int> p0_pos(31);
  for (int i = 0; i < 31; i++) p0_pos[i] = pos++;
  int push_temp_p = pos++;
  int pop_temp_p = pos++;
  vector<int> under_p_pos(31);
  pos--;
  for (int i = 30; i >= 0; i--) {
    under_p_pos[i] = pos++;
  }
  vector<int> clean_p_pos(31);
  for (int i = 0; i < 31; i++) clean_p_pos[i] = pos++;
  vector<int> add_push(l), add_pop(l);
  for (int jj = 0; jj < l; jj++) {
    add_push[jj] = pos++;
    add_pop[jj] = pos++;
  }
  int h_pos = pos++;
  int total_n = h_pos;
  // now fill prog
  vector<string> prog(total_n + 1);
  // setup
  for (int ii = 0; ii < 31; ii++) {
    int bb = 30 - ii;
    int p = setup_pos[ii];
    int s = bit_val[bb];
    int nxt = (ii < 30 ? setup_pos[ii + 1] : a_pos[0]);
    prog[p] = "POP " + to_string(wrong_a) + " GOTO 1 PUSH " + to_string(s) + " GOTO " + to_string(nxt);
  }
  // pop gadgets
  int done_p = push_temp_p;
  for (int i = 0; i < 31; i++) {
    int ap = a_pos[i];
    int ones = one_sym[i];
    int was1p = p0_pos[i];
    int bp = b_pos[i];
    int cp = c_pos[i];
    int zeros = zero_sym[i];
    int was0p = (i < 30 ? a_pos[i + 1] : under_p_pos[30]);
    prog[ap] = "POP " + to_string(ones) + " GOTO " + to_string(was1p) + " PUSH " + to_string(temp_sym) + " GOTO " + to_string(bp);
    prog[bp] = "POP " + to_string(temp_sym) + " GOTO " + to_string(cp) + " PUSH " + to_string(wrong_a) + " GOTO 1";
    prog[cp] = "POP " + to_string(zeros) + " GOTO " + to_string(was0p) + " PUSH " + to_string(wrong_a) + " GOTO 1";
  }
  // push1
  prog[p1_pos[0]] = "POP " + to_string(wrong_a) + " GOTO 1 PUSH " + to_string(one_sym[0]) + " GOTO " + to_string(done_p);
  for (int j = 1; j < 30; j++) {
    prog[p1_pos[j]] = "POP " + to_string(wrong_a) + " GOTO 1 PUSH " + to_string(one_sym[j]) + " GOTO " + to_string(p1_pos[j - 1]);
  }
  // push0
  for (int i = 0; i <= 30; i++) {
    int nextp = (i == 0 ? done_p : p1_pos[i - 1]);
    int zs = zero_sym[i];
    prog[p0_pos[i]] = "POP " + to_string(wrong_a) + " GOTO 1 PUSH " + to_string(zs) + " GOTO " + to_string(nextp);
  }
  // body
  prog[push_temp_p] = "POP 3 GOTO 1 PUSH " + to_string(temp_sym) + " GOTO " + to_string(pop_temp_p);
  prog[pop_temp_p] = "POP " + to_string(temp_sym) + " GOTO " + to_string(a_pos[0]) + " PUSH " + to_string(wrong_a) + " GOTO 1";
  // under push
  int clean_start_pos = clean_p_pos[0];
  for (int i = 30; i >= 0; i--) {
    int p = under_p_pos[i];
    int zs = zero_sym[i];
    int nxt = (i > 0 ? under_p_pos[i - 1] : clean_start_pos);
    prog[p] = "POP " + to_string(wrong_a) + " GOTO 1 PUSH " + to_string(zs) + " GOTO " + to_string(nxt);
  }
  // clean
  int added_or_h = (l == 0 ? h_pos : add_push[0]);
  for (int i = 0; i < 31; i++) {
    int p = clean_p_pos[i];
    int zs = zero_sym[i];
    int nxt = (i < 30 ? clean_p_pos[i + 1] : added_or_h);
    prog[p] = "POP " + to_string(zs) + " GOTO " + to_string(nxt) + " PUSH " + to_string(wrong_a) + " GOTO 1";
  }
  // added
  int prev_n = h_pos;
  for (int jj = l - 1; jj >= 0; jj--) {
    int popp = add_pop[jj];
    prog[popp] = "POP " + to_string(added_b) + " GOTO " + to_string(prev_n) + " PUSH " + to_string(wrong_a) + " GOTO 1";
    int pushp = add_push[jj];
    prog[pushp] = "POP " + to_string(wrong_a) + " GOTO 1 PUSH " + to_string(added_b) + " GOTO " + to_string(popp);
    prev_n = pushp;
  }
  // halt
  prog[h_pos] = "HALT PUSH 1 GOTO " + to_string(h_pos);
  // output
  cout << total_n << endl;
  for (int i = 1; i <= total_n; i++) {
    cout << prog[i] << endl;
  }
  return 0;
}