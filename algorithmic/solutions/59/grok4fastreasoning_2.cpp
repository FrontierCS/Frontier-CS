#include <bits/stdc++.h>
using namespace std;

tuple<int, vector<int>, int> do_step(const vector<int>& buf, int c_next, int i, int n, int k) {
  int b = buf.size();
  int avail = min(3, n - i + 1);
  if (k >= avail || k < 0) return {-1, {}, -1};
  // compute f0, f1, f2
  vector<int> f(3, -1);
  for (int m = 0; m < 3; ++m) {
    if (m < b) {
      f[m] = buf[m];
    } else {
      int off = m - b;
      int val = c_next + off;
      if (val > n) return {-1, {}, -1};
      f[m] = val;
    }
  }
  int f0 = f[0];
  int f1 = (avail > 1 ? f[1] : -1);
  int f2 = (avail > 2 ? f[2] : -1);
  int ai = f[k];
  int new_f0 = (k == 1 ? f0 : f1);
  int new_f1 = (k == 2 ? f0 : f2);
  bool took_next = (k >= b);
  int new_c = c_next;
  if (took_next) {
    new_c = ai + 1;
  }
  vector<int> new_buf;
  if (new_f0 == new_c) {
    new_buf = {};
    return {ai, new_buf, new_c};
  } else {
    new_buf.push_back(new_f0);
    if (new_f1 == new_c) {
      return {ai, new_buf, new_c};
    } else {
      new_buf.push_back(new_f1);
      return {ai, new_buf, new_c};
    }
  }
  return {ai, new_buf, new_c}; // unreachable
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  int n;
  cin >> n;
  vector<int> a(n + 1, 0);
  vector<int> current_buf;
  int c_next = 1;
  int total_queries = 0;
  int max_queries = (5 * n / 3) + 5;
  int pos = 1;
  while (pos <= n) {
    int group_size = min(3, n - pos + 1);
    int num_steps = group_size;
    int max_conf = 1;
    for (int g = 0; g < num_steps; ++g) max_conf *= 3;
    vector<vector<int>> sim_placed(max_conf, vector<int>(num_steps));
    vector<vector<int>> sim_final_buf(max_conf);
    vector<int> sim_final_cnext(max_conf);
    vector<bool> valid(max_conf, false);
    int conf_id = 0;
    vector<int> ks(num_steps);
    function<void(int)> gen = [&](int step) {
      if (step == num_steps) {
        // simulate
        vector<int> temp_buf = current_buf;
        int temp_c = c_next;
        bool ok = true;
        vector<int> temp_placed;
        for (int s = 0; s < num_steps; ++s) {
          int curr_i = pos + s;
          auto [ai_temp, new_temp_buf, new_temp_c] = do_step(temp_buf, temp_c, curr_i, n, ks[s]);
          if (ai_temp == -1) {
            ok = false;
            break;
          }
          temp_placed.push_back(ai_temp);
          temp_buf = new_temp_buf;
          temp_c = new_temp_c;
        }
        if (ok) {
          sim_placed[conf_id] = temp_placed;
          sim_final_buf[conf_id] = temp_buf;
          sim_final_cnext[conf_id] = temp_c;
          valid[conf_id] = true;
        }
        ++conf_id;
        return;
      }
      for (int kk = 0; kk < 3; ++kk) {
        ks[step] = kk;
        gen(step + 1);
      }
    };
    gen(0);
    // now possible
    vector<int> possible;
    for (int ii = 0; ii < max_conf; ++ii) {
      if (valid[ii]) possible.push_back(ii);
    }
    int asks = 0;
    while (possible.size() > 1 && total_queries < max_queries - 10) { // safe margin
      // candidate queries
      vector<pair<int, int>> cands;
      // local
      for (int p1 = 0; p1 < group_size; ++p1) {
        for (int p2 = p1 + 1; p2 < group_size; ++p2) {
          cands.emplace_back(pos + p1, pos + p2);
        }
      }
      // references
      vector<int> refs;
      if (pos > 1) {
        // previous 3
        for (int r = 0; r < min(3, pos - 1); ++r) {
          refs.push_back(pos - 1 - r);
        }
      } else {
        // future for first: only 4 if group_size==3
        int fut = pos + group_size;
        if (fut <= n) {
          refs.push_back(fut); // only to 4
        }
      }
      for (int p = 0; p < group_size; ++p) {
        for (int r : refs) {
          int i1 = pos + p;
          int i2 = r;
          if (i1 > i2) swap(i1, i2);
          cands.emplace_back(i1, i2);
        }
      }
      // find best
      int best_max = possible.size() + 1;
      pair<int, int> best_pair = {-1, -1};
      for (auto qu : cands) {
        int i = qu.first;
        int j = qu.second;
        // compute can_less, can_greater for each conf? No, count of conf that can do less, can do greater
        int num_can_less = 0;
        int num_can_greater = 0;
        for (int cf : possible) {
          int ai_pred = sim_placed[cf][i - pos];
          bool can_l = false;
          bool can_g = false;
          if (j < pos) { // previous known
            int aj = a[j];
            if (ai_pred < aj) can_l = true;
            if (ai_pred > aj) can_g = true;
          } else if (pos == 1 && j == pos + group_size) { // to 4, first group
            // sim k4
            int next_i = pos + group_size;
            vector<int> tbuf = sim_final_buf[cf];
            int tc = sim_final_cnext[cf];
            for (int k4 = 0; k4 < 3; ++k4) {
              auto [a4, _, __] = do_step(tbuf, tc, next_i, n, k4);
              if (a4 != -1) {
                if (ai_pred < a4) can_l = true;
                if (ai_pred > a4) can_g = true;
              }
            }
          } else {
            // local, exact
            int aj_pred = sim_placed[cf][j - pos];
            if (ai_pred < aj_pred) can_l = true;
            if (ai_pred > aj_pred) can_g = true;
          }
          if (can_l) ++num_can_less;
          if (can_g) ++num_can_greater;
        }
        int this_max = max(num_can_less, num_can_greater);
        if (this_max < best_max) {
          best_max = this_max;
          best_pair = qu;
        }
      }
      if (best_pair.first == -1) break; // no more
      // ask
      int qi = best_pair.first;
      int qj = best_pair.second;
      cout << "? " << qi << " " << qj << endl;
      cout.flush();
      ++total_queries;
      ++asks;
      string resp;
      cin >> resp;
      bool is_less = (resp == "<");
      // filter possible
      vector<int> new_possible;
      for (int cf : possible) {
        int ai_pred = sim_placed[cf][qi - pos];
        bool matches = false;
        if (qj < pos) { // previous
          int aj = a[qj];
          matches = (ai_pred < aj) == is_less;
        } else if (pos == 1 && qj == pos + group_size) { // to 4
          int next_i = pos + group_size;
          vector<int> tbuf = sim_final_buf[cf];
          int tc = sim_final_cnext[cf];
          for (int k4 = 0; k4 < 3; ++k4) {
            auto [a4, _, __] = do_step(tbuf, tc, next_i, n, k4);
            if (a4 != -1 && (ai_pred < a4) == is_less) {
              matches = true;
              break;
            }
          }
        } else { // local
          int aj_pred = sim_placed[cf][qj - pos];
          matches = (ai_pred < aj_pred) == is_less;
        }
        if (matches) new_possible.push_back(cf);
      }
      possible = new_possible;
    }
    // now take the first (assume unique)
    if (possible.empty()) {
      // error, but shouldn't
      assert(false);
    }
    int chosen = possible[0];
    for (int s = 0; s < group_size; ++s) {
      a[pos + s] = sim_placed[chosen][s];
    }
    current_buf = sim_final_buf[chosen];
    c_next = sim_final_cnext[chosen];
    pos += group_size;
  }
  // output
  cout << "! ";
  for (int i = 1; i <= n; ++i) {
    cout << a[i] << (i < n ? " " : "\n");
  }
  cout.flush();
  return 0;
}