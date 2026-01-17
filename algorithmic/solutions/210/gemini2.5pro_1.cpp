#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <cmath>
#include <algorithm>
#include <map>

using namespace std;

// --- Data Structures ---

struct Point {
    int r, c;

    bool operator==(const Point& other) const {
        return r == other.r && c == other.c;
    }
    bool operator!=(const Point& other) const {
        return !(*this == other);
    }
     bool operator<(const Point& other) const {
        if (r != other.r) return r < other.r;
        return c < other.c;
    }
};

struct BlueBase {
    int id;
    Point pos;
    long long fuel_supply;
    long long missile_supply;
};

struct RedBase {
    int id;
    Point pos;
    long long defense;
    long long value;
    long long damage_taken = 0;
    bool is_destroyed = false;
    vector<Point> attack_positions;
    int assigned_fighter_id = -1;
};

struct Fighter {
    int id;
    Point pos;
    long long fuel = 0;
    long long missiles = 0;
    long long max_fuel;
    long long max_missiles;
};

struct FighterAgent {
    enum Status { IDLE, GOING_TO_BASE, AT_BASE, GOING_TO_TARGET, AT_TARGET };
    Status status = IDLE;

    int fighter_id;
    int target_red_base_id = -1;
    int target_blue_base_id = -1;
    Point target_attack_pos;
    Point destination;
    vector<Point> path;

    FighterAgent(int id) : fighter_id(id) {}
};

// --- Globals ---

int n, m, k;
vector<string> initial_grid;
vector<string> path_grid;
vector<BlueBase> blue_bases;
vector<RedBase> red_bases;
vector<Fighter> fighters;
vector<FighterAgent> fighter_agents;

int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};

// --- Pathfinding ---

struct BFSResult {
    vector<vector<int>> dist;
    vector<vector<Point>> parent;
};

BFSResult bfs_from(Point start) {
    BFSResult res;
    res.dist.assign(n, vector<int>(m, -1));
    res.parent.assign(n, vector<Point>(m, {-1, -1}));
    
    queue<Point> q;

    if (start.r < 0 || start.r >= n || start.c < 0 || start.c >= m || path_grid[start.r][start.c] == '#') {
        return res;
    }

    q.push(start);
    res.dist[start.r][start.c] = 0;

    while (!q.empty()) {
        Point u = q.front();
        q.pop();

        for (int i = 0; i < 4; ++i) {
            Point v = {u.r + dr[i], u.c + dc[i]};
            if (v.r >= 0 && v.r < n && v.c >= 0 && v.c < m &&
                path_grid[v.r][v.c] != '#' && res.dist[v.r][v.c] == -1) {
                res.dist[v.r][v.c] = res.dist[u.r][u.c] + 1;
                res.parent[v.r][v.c] = u;
                q.push(v);
            }
        }
    }
    return res;
}

vector<Point> reconstruct_path(Point start, Point end, const BFSResult& bfs_res) {
    vector<Point> path;
    if (bfs_res.dist[end.r][end.c] == -1) {
        return path;
    }
    Point curr = end;
    while (curr != start) {
        path.push_back(curr);
        curr = bfs_res.parent[curr.r][curr.c];
        if (curr.r == -1) return {};
    }
    reverse(path.begin(), path.end());
    return path;
}

// --- Utility ---

int get_direction(Point from, Point to) {
    if (to.r < from.r) return 0;
    if (to.r > from.r) return 1;
    if (to.c < from.c) return 2;
    if (to.c > from.c) return 3;
    return -1;
}

// --- Main Logic ---

void assign_task_to_agent(FighterAgent& agent);
void find_and_set_new_base(FighterAgent& agent);

void update_agents(vector<string>& commands) {
    for (auto& agent : fighter_agents) {
        if (agent.status == FighterAgent::IDLE) {
            assign_task_to_agent(agent);
        }
    }

    for (auto& agent : fighter_agents) {
        Fighter& f = fighters[agent.fighter_id];

        if (agent.status == FighterAgent::GOING_TO_BASE || agent.status == FighterAgent::GOING_TO_TARGET) {
            if (f.pos == agent.destination) {
                agent.path.clear();
                if (agent.status == FighterAgent::GOING_TO_BASE) agent.status = FighterAgent::AT_BASE;
                else agent.status = FighterAgent::AT_TARGET;
            } else {
                if (!agent.path.empty()) {
                    if (f.fuel > 0) {
                        Point next_pos = agent.path.front();
                        agent.path.erase(agent.path.begin());
                        int dir = get_direction(f.pos, next_pos);
                        commands.push_back("move " + to_string(f.id) + " " + to_string(dir));
                        f.fuel--;
                        f.pos = next_pos;
                    }
                } else {
                    BFSResult res = bfs_from(f.pos);
                    agent.path = reconstruct_path(f.pos, agent.destination, res);
                    if (agent.path.empty()) {
                        if(agent.target_red_base_id != -1) red_bases[agent.target_red_base_id].assigned_fighter_id = -1;
                        agent.status = FighterAgent::IDLE;
                    }
                }
            }
        }

        if (agent.status == FighterAgent::AT_BASE) {
            if(agent.target_red_base_id == -1) {
                agent.status = FighterAgent::IDLE;
                continue;
            }
            BlueBase& bb = blue_bases[agent.target_blue_base_id];
            RedBase& rb = red_bases[agent.target_red_base_id];

            BFSResult res_from_ap = bfs_from(agent.target_attack_pos);
            int min_dist_to_base_from_ap = 1e9;
            for(const auto& blue_base : blue_bases) {
                if (res_from_ap.dist[blue_base.pos.r][blue_base.pos.c] != -1) {
                    min_dist_to_base_from_ap = min(min_dist_to_base_from_ap, res_from_ap.dist[blue_base.pos.r][blue_base.pos.c]);
                }
            }
            if(min_dist_to_base_from_ap == 1e9) min_dist_to_base_from_ap = 0;

            int dist_base_to_ap = bfs_from(f.pos).dist[agent.target_attack_pos.r][agent.target_attack_pos.c];
            if (dist_base_to_ap == -1) {
                red_bases[agent.target_red_base_id].assigned_fighter_id = -1;
                agent.status = FighterAgent::IDLE;
                continue;
            }

            long long fuel_to_get = dist_base_to_ap + min_dist_to_base_from_ap;
            long long fuel_to_take = min({f.max_fuel - f.fuel, bb.fuel_supply, fuel_to_get});
            if (fuel_to_take > 0) {
                commands.push_back("fuel " + to_string(f.id) + " " + to_string(fuel_to_take));
                f.fuel += fuel_to_take;
                bb.fuel_supply -= fuel_to_take;
            }

            long long missiles_needed = rb.defense - rb.damage_taken;
            long long missiles_to_take = min({f.max_missiles - f.missiles, bb.missile_supply, missiles_needed});
            if (missiles_to_take > 0) {
                commands.push_back("missile " + to_string(f.id) + " " + to_string(missiles_to_take));
                f.missiles += missiles_to_take;
                bb.missile_supply -= missiles_to_take;
            }

            if (f.missiles > 0 && f.fuel >= dist_base_to_ap) {
                agent.status = FighterAgent::GOING_TO_TARGET;
                agent.destination = agent.target_attack_pos;
                BFSResult res = bfs_from(f.pos);
                agent.path = reconstruct_path(f.pos, agent.destination, res);
            } else if (bb.missile_supply == 0 && f.missiles < f.max_missiles && missiles_needed > f.missiles) {
                find_and_set_new_base(agent);
            }
        }

        if (agent.status == FighterAgent::AT_TARGET) {
            if(agent.target_red_base_id == -1) {
                agent.status = FighterAgent::IDLE;
                continue;
            }
            RedBase& rb = red_bases[agent.target_red_base_id];
            if (rb.is_destroyed) {
                agent.status = FighterAgent::IDLE;
                rb.assigned_fighter_id = -1;
                continue;
            }

            if (f.missiles == 0) {
                find_and_set_new_base(agent);
                continue;
            }

            long long missiles_to_fire = min(f.missiles, rb.defense - rb.damage_taken);
            if (missiles_to_fire > 0) {
                int dir = get_direction(f.pos, rb.pos);
                commands.push_back("attack " + to_string(f.id) + " " + to_string(dir) + " " + to_string(missiles_to_fire));
                f.missiles -= missiles_to_fire;
                rb.damage_taken += missiles_to_fire;
            }

            if (rb.damage_taken >= rb.defense) {
                rb.is_destroyed = true;
                path_grid[rb.pos.r][rb.pos.c] = '.';
                agent.status = FighterAgent::IDLE;
                rb.assigned_fighter_id = -1;
            }
        }
    }
}

void find_and_set_new_base(FighterAgent& agent) {
    Fighter& f = fighters[agent.fighter_id];
    
    int best_bb_id = -1;
    int min_dist = 1e9;
    BFSResult res_from_f = bfs_from(f.pos);

    for (int i = 0; i < blue_bases.size(); ++i) {
        if (blue_bases[i].missile_supply > 0) {
            int d = res_from_f.dist[blue_bases[i].pos.r][blue_bases[i].pos.c];
            if (d != -1 && d < min_dist) {
                min_dist = d;
                best_bb_id = i;
            }
        }
    }
    
    if (best_bb_id == -1) {
        min_dist = 1e9;
        for (int i = 0; i < blue_bases.size(); ++i) {
            if (blue_bases[i].fuel_supply > 0) {
                int d = res_from_f.dist[blue_bases[i].pos.r][blue_bases[i].pos.c];
                if (d != -1 && d < min_dist) {
                    min_dist = d;
                    best_bb_id = i;
                }
            }
        }
    }

    if (best_bb_id != -1) {
        agent.status = FighterAgent::GOING_TO_BASE;
        agent.target_blue_base_id = best_bb_id;
        agent.destination = blue_bases[best_bb_id].pos;
        agent.path = reconstruct_path(f.pos, agent.destination, res_from_f);
    } else {
        agent.status = FighterAgent::IDLE;
        if (agent.target_red_base_id != -1) {
            red_bases[agent.target_red_base_id].assigned_fighter_id = -1;
        }
    }
}

void assign_task_to_agent(FighterAgent& agent) {
    Fighter& f = fighters[agent.fighter_id];
    
    int best_target_id = -1;
    double max_score = -1.0;
    int mission_bb_id = -1;
    Point mission_ap;

    BFSResult res_from_f = bfs_from(f.pos);

    for (int i = 0; i < red_bases.size(); ++i) {
        if (red_bases[i].is_destroyed || red_bases[i].assigned_fighter_id != -1) continue;

        int best_bb_id_for_rb = -1;
        Point best_ap_for_rb;
        int min_round_trip_dist = 1e9;

        for (const auto& ap : red_bases[i].attack_positions) {
            BFSResult res_from_ap = bfs_from(ap);
            for (int bb_idx = 0; bb_idx < blue_bases.size(); ++bb_idx) {
                if (blue_bases[bb_idx].missile_supply > 0) {
                    int dist_bb_ap = res_from_ap.dist[blue_bases[bb_idx].pos.r][blue_bases[bb_idx].pos.c];
                    if (dist_bb_ap != -1) {
                        if (dist_bb_ap * 2 < min_round_trip_dist && (long long)dist_bb_ap * 2 <= f.max_fuel) {
                            min_round_trip_dist = dist_bb_ap * 2;
                            best_bb_id_for_rb = bb_idx;
                            best_ap_for_rb = ap;
                        }
                    }
                }
            }
        }
        
        if (best_bb_id_for_rb == -1) continue;

        int dist_f_to_bb = res_from_f.dist[blue_bases[best_bb_id_for_rb].pos.r][blue_bases[best_bb_id_for_rb].pos.c];
        if (dist_f_to_bb == -1) continue;

        long long missiles_needed = red_bases[i].defense - red_bases[i].damage_taken;
        long long num_trips = (missiles_needed + f.max_missiles - 1) / f.max_missiles;
        long long time_estimate = dist_f_to_bb + (num_trips * min_round_trip_dist);

        if (time_estimate == 0) time_estimate = 1;
        double score = (double)red_bases[i].value / time_estimate;

        if (score > max_score) {
            max_score = score;
            best_target_id = i;
            mission_bb_id = best_bb_id_for_rb;
            mission_ap = best_ap_for_rb;
        }
    }
    
    if (best_target_id != -1) {
        agent.target_red_base_id = best_target_id;
        red_bases[best_target_id].assigned_fighter_id = agent.fighter_id;
        agent.target_blue_base_id = mission_bb_id;
        agent.target_attack_pos = mission_ap;

        if (f.pos == blue_bases[mission_bb_id].pos) {
            agent.status = FighterAgent::AT_BASE;
        } else {
            agent.status = FighterAgent::GOING_TO_BASE;
            agent.destination = blue_bases[mission_bb_id].pos;
            agent.path = reconstruct_path(f.pos, agent.destination, res_from_f);
        }
    }
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> m;
    initial_grid.resize(n);
    for (int i = 0; i < n; ++i) cin >> initial_grid[i];
    path_grid = initial_grid;

    int num_blue_bases;
    cin >> num_blue_bases;
    for (int i = 0; i < num_blue_bases; ++i) {
        BlueBase b;
        b.id = i;
        cin >> b.pos.r >> b.pos.c;
        long long d_dummy, v_dummy;
        cin >> b.fuel_supply >> b.missile_supply >> d_dummy >> v_dummy;
        blue_bases.push_back(b);
    }

    int num_red_bases;
    cin >> num_red_bases;
    for (int i = 0; i < num_red_bases; ++i) {
        RedBase r;
        r.id = i;
        cin >> r.pos.r >> r.pos.c;
        long long g_dummy, c_dummy;
        cin >> g_dummy >> c_dummy >> r.defense >> r.value;
        for (int j = 0; j < 4; ++j) {
            Point ap = {r.pos.r + dr[j], r.pos.c + dc[j]};
            if (ap.r >= 0 && ap.r < n && ap.c >= 0 && ap.c < m && initial_grid[ap.r][ap.c] != '#') {
                r.attack_positions.push_back(ap);
            }
        }
        if(r.defense > 0) red_bases.push_back(r);
    }

    cin >> k;
    for (int i = 0; i < k; ++i) {
        Fighter f;
        f.id = i;
        cin >> f.pos.r >> f.pos.c >> f.max_fuel >> f.max_missiles;
        fighters.push_back(f);
        fighter_agents.emplace_back(i);
    }

    for (int frame = 1; frame <= 15000; ++frame) {
        vector<string> commands;
        update_agents(commands);

        for (const auto& cmd : commands) {
            cout << cmd << endl;
        }
        cout << "OK" << endl;

        bool all_destroyed = true;
        for (const auto& rb : red_bases) {
            if (!rb.is_destroyed) {
                all_destroyed = false;
                break;
            }
        }
        if (all_destroyed) {
            break;
        }
    }

    return 0;
}