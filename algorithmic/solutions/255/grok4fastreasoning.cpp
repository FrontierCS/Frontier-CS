#include <bits/stdc++.h>
using namespace std;

int query(const vector<int>& L, const vector<int>& R) {
  int ls = L.size();
  int rs = R.size();
  cout << "? " << ls << " " << rs << endl;
  for (int x : L) cout << x << " ";
  cout << endl;
  for (int x : R) cout << x << " ";
  cout << endl;
  cout.flush();
  int f;
  cin >> f;
  return f;
}

int single_query(int a, int b) {
  vector<int> L = {a};
  vector<int> R = {b};
  return query(L, R);
}

void print_answer(const vector<int>& zs) {
  cout << "! " << zs.size();
  for (int i : zs) cout << " " << i;
  cout << endl;
  cout.flush();
}

int find_single_pos(const vector<int>& setv, const vector<int>& ref_set, bool& detected) {
  detected = false;
  int sz = setv.size();
  int low = 0;
  int high = sz - 1;
  while (low < high) {
    int mid = low + (high - low) / 2;
    vector<int> test_set(setv.begin() + low, setv.begin() + mid + 1);
    int f = query(test_set, ref_set);
    if (f != 0) {
      detected = true;
      high = mid;
    } else {
      low = mid + 1;
    }
  }
  return low;
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  int t;
  cin >> t;
  for (int test = 0; test < t; test++) {
    int num_magnets;
    cin >> num_magnets;
    int alone = -1;
    int process_size = num_magnets;
    if (num_magnets % 2 == 1) {
      alone = num_magnets;
      process_size = num_magnets - 1;
    }
    int m = process_size / 2;
    vector<int> pair_left(m), pair_right(m);
    for (int i = 0; i < m; i++) {
      pair_left[i] = 2 * i + 1;
      pair_right[i] = 2 * i + 2;
    }
    bool found_known = false;
    int known = -1;
    // First matching
    for (int i = 0; i < m; i++) {
      int f = single_query(pair_left[i], pair_right[i]);
      if (f != 0) {
        found_known = true;
        known = pair_left[i];
        break;
      }
    }
    if (found_known) {
      goto classify;
    }
    // Second matching on pair_left
    int m2 = m;
    int num_p2 = m2 / 2;
    for (int j = 0; j < num_p2; j++) {
      int a = pair_left[2 * j];
      int b = pair_left[2 * j + 1];
      int f = single_query(a, b);
      if (f != 0) {
        found_known = true;
        known = a;
        break;
      }
    }
    if (found_known) {
      goto classify;
    }
    // Third matching on pair_right
    int m3 = m;
    int num_p3 = m3 / 2;
    for (int j = 0; j < num_p3; j++) {
      int a = pair_right[2 * j];
      int b = pair_right[2 * j + 1];
      int f = single_query(a, b);
      if (f != 0) {
        found_known = true;
        known = a;
        break;
      }
    }
    if (found_known) {
      goto classify;
    }
    // Single case
    bool detected1 = false;
    int pos1 = find_single_pos(pair_left, pair_right, detected1);
    int cand1 = pair_left[pos1];
    if (detected1) {
      known = cand1;
      found_known = true;
    } else {
      bool detected2 = false;
      int pos2 = find_single_pos(pair_right, pair_left, detected2);
      int cand2 = pair_right[pos2];
      if (detected2) {
        known = cand2;
        found_known = true;
      } else {
        // alone tests if odd
        if (alone != -1) {
          found_known = false;
          for (int j = 0; j < m; j++) {
            int f = single_query(alone, pair_left[j]);
            if (f != 0) {
              known = alone;
              found_known = true;
              break;
            }
          }
          if (!found_known) {
            for (int j = 0; j < m; j++) {
              int f = single_query(alone, pair_right[j]);
              if (f != 0) {
                known = alone;
                found_known = true;
                break;
              }
            }
          }
        }
        assert(found_known); // should not reach here
      }
    }
classify:
    // classify all
    vector<int> demag;
    int orig_n = num_magnets;
    for (int i = 1; i <= orig_n; i++) {
      if (i == known) continue;
      int f = single_query(i, known);
      if (f == 0) demag.push_back(i);
    }
    print_answer(demag);
  }
  return 0;
}