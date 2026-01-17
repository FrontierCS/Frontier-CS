#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <map>
#include <cmath>
#include <algorithm>

using namespace std;

// --- Data Structures ---

struct Point {
    int r, c;
    bool operator<(const Point& other) const {
        if (r != other.r) return r < other.r;
        return c < other.c;
    }
    bool operator==(const Point& other) const {
        return r == other.r && c == other.c;
    }
};

struct BlueBase {
    int id;
    Point pos;
    long long initial_g, initial_c;
    long long g, c;
};

struct RedBase {
    int id;
    Point pos;
    int d, v;
    int health;
};

struct Fighter {
    int id;
    Point pos;
    int G, C;
    int fuel, missiles;
};

// --- Agent and State ---

enum class AgentStatus {
    IDLE,
    REFUELING,
    MOVING_TO_TARGET,
    ATTACKING,
    MOVING_TO_BASE
};

struct FighterAgent {
    int fighter_id;
    AgentStatus status = AgentStatus::IDLE;

    int target_red_base_id = -1;
    int supply_blue_base_id = -1;
    int return_blue_base_id = -1;

    vector<Point> path;
    int path_idx = 0;

    int fuel_needed = 0;
    int missiles_to_load = 0;
};

// --- Global Game State ---

int n, m;
vector<string> grid;
vector<BlueBase> blue_bases;
vector<RedBase> red_bases;
vector<Fighter> fighters;
vector<FighterAgent> agents;

map<Point, int> pos_to_blue_base_id;
map<Point, int> pos_to_red_base_id;

vector<int> red_base_claimed_damage;

// --- Pathfinding ---

const int dr[] = {-1, 1, 0, 0};
const int dc[] = {0, 0, -1, 1};

vector<Point> bfs(Point start, Point target, bool target_is_area) {
    if (target_is_area) {
        bool adjacent = false;
        for (int i = 0; i < 4; ++i) {
            Point adj = {start.r + dr[i], start.c + dc[i]};
            if (adj.r == target.r && adj.c == target.c) {
                adjacent = true;
                break;
            }
        }
        if (adjacent) return {start};
    } else {
        if (start == target) return {start};
    }
    
    queue<Point> q;
    q.push(start);
    map<Point, Point> parent;
    parent[start] = {-1, -1};

    Point dest_node = {-1, -1};

    while (!q.empty()) {
        Point curr = q.front();
        q.pop();

        if (target_is_area) {
            for (int i = 0; i < 4; ++i) {
                Point adj = {curr.r + dr[i], curr.c + dc[i]};
                if (adj.r == target.r && adj.c == target.c) {
                    dest_node = curr;
                    goto found_path;
                }
            }
        } else {
            if (curr.r == target.r && curr.c == target.c) {
                dest_node = curr;
                goto found_path;
            }
        }

        for (int i = 0; i < 4; ++i) {
            Point next = {curr.r + dr[i], curr.c + dc[i]};
            if (next.r >= 0 && next.r < n && next.c >= 0 && next.c < m && grid[next.r][next.c] != '#' && parent.find(next) == parent.end()) {
                parent[next] = curr;
                q.push(next);
            }
        }
    }

found_path:
    if (dest_node.r == -1) {
        return {};
    }

    vector<Point> path;
    Point p = dest_node;
    while (p.r != -1) {
        path.push_back(p);
        p = parent[p];
    }
    reverse(path.begin(), path.end());
    return path;
}

int get_dir(Point from, Point to) {
    if (to.r < from.r) return 0; // up
    if (to.r > from.r) return 1; // down
    if (to.c < from.c) return 2; // left
    if (to.c > from.c) return 3; // right
    return -1;
}

// --- Main Logic ---

void assign_task(int agent_id) {
    FighterAgent& agent = agents[agent_id];
    Fighter& fighter = fighters[agent.fighter_id];

    auto it = pos_to_blue_base_id.find(fighter.pos);
    if (it == pos_to_blue_base_id.end()) return;
    int current_base_id = it->second;

    if (blue_bases[current_base_id].c == 0) return;

    double best_score = -1.0;
    int best_target_id = -1;
    int best_return_base_id = -1;

    for (const auto& rb : red_bases) {
        if (rb.health <= 0) continue;
        if (rb.health - red_base_claimed_damage[rb.id] <= 0) continue;


        auto path_to_target = bfs(fighter.pos, rb.pos, true);
        if (path_to_target.empty()) continue;
        int dist_to = path_to_target.size() - 1;
        
        Point attack_pos = path_to_target.back();
        
        int best_dist_from = 1e9;
        int current_best_return_base = -1;
        for (const auto& bb : blue_bases) {
            auto path_from_target = bfs(attack_pos, bb.pos, false);
            if (!path_from_target.empty()) {
                int dist = path_from_target.size() - 1;
                if (dist < best_dist_from) {
                    best_dist_from = dist;
                    current_best_return_base = bb.id;
                }
            }
        }

        if (current_best_return_base == -1) continue;

        if (dist_to + best_dist_from > fighter.G) continue;
        
        double score = (double)rb.v / (dist_to + best_dist_from + 1.0);

        if (score > best_score) {
            best_score = score;
            best_target_id = rb.id;
            best_return_base_id = current_best_return_base;
        }
    }
    
    if (best_target_id != -1) {
        agent.status = AgentStatus::REFUELING;
        agent.target_red_base_id = best_target_id;
        agent.supply_blue_base_id = current_base_id;
        agent.return_blue_base_id = best_return_base_id;

        auto path_to = bfs(blue_bases[agent.supply_blue_base_id].pos, red_bases[agent.target_red_base_id].pos, true);
        Point attack_pos = path_to.back();
        auto path_from = bfs(attack_pos, blue_bases[agent.return_blue_base_id].pos, false);
        
        agent.fuel_needed = (path_to.empty() ? 0 : path_to.size()-1) + (path_from.empty() ? 0 : path_from.size()-1);
        agent.missiles_to_load = min({fighter.C, (int)blue_bases[agent.supply_blue_base_id].c, red_bases[agent.target_red_base_id].health - red_base_claimed_damage[agent.target_red_base_id]});

        if (agent.missiles_to_load > 0) {
            red_base_claimed_damage[agent.target_red_base_id] += agent.missiles_to_load;
        } else {
            agent.status = AgentStatus::IDLE;
        }
    }
}


void step_agent(int agent_id, vector<string>& commands) {
    FighterAgent& agent = agents[agent_id];
    Fighter& fighter = fighters[agent.fighter_id];
    
    if (agent.status == AgentStatus::IDLE) {
        assign_task(agent_id);
    }

    if (agent.status == AgentStatus::REFUELING) {
        bool fuel_ok = fighter.fuel >= agent.fuel_needed;
        bool missiles_ok = fighter.missiles >= agent.missiles_to_load;

        if (!fuel_ok) {
            long long fuel_to_take = min((long long)agent.fuel_needed - fighter.fuel, blue_bases[agent.supply_blue_base_id].g);
            if (fuel_to_take > 0) {
                commands.push_back("fuel " + to_string(fighter.id) + " " + to_string(fuel_to_take));
                fighter.fuel += fuel_to_take;
                blue_bases[agent.supply_blue_base_id].g -= fuel_to_take;
            }
        }
        if (!missiles_ok) {
            long long missiles_to_take = min((long long)agent.missiles_to_load - fighter.missiles, blue_bases[agent.supply_blue_base_id].c);
            if (missiles_to_take > 0) {
                commands.push_back("missile " + to_string(fighter.id) + " " + to_string(missiles_to_take));
                fighter.missiles += missiles_to_take;
                blue_bases[agent.supply_blue_base_id].c -= missiles_to_take;
            }
        }

        if (fighter.fuel >= agent.fuel_needed && fighter.missiles >= agent.missiles_to_load) {
            agent.status = AgentStatus::MOVING_TO_TARGET;
            agent.path = bfs(fighter.pos, red_bases[agent.target_red_base_id].pos, true);
            agent.path_idx = 1;
        }
        return;
    }

    if (agent.status == AgentStatus::MOVING_TO_TARGET) {
        if (red_bases[agent.target_red_base_id].health <= 0) {
            red_base_claimed_damage[agent.target_red_base_id] -= agent.missiles_to_load;
            agent.status = AgentStatus::MOVING_TO_BASE;
            agent.path = bfs(fighter.pos, blue_bases[agent.return_blue_base_id].pos, false);
            agent.path_idx = 1;
            if (fighter.pos == blue_bases[agent.return_blue_base_id].pos) {
                 agent.status = AgentStatus::IDLE;
            }
            return;
        }
        
        if (agent.path_idx < agent.path.size()) {
            Point next_pos = agent.path[agent.path_idx];
            int dir = get_dir(fighter.pos, next_pos);
            commands.push_back("move " + to_string(fighter.id) + " " + to_string(dir));
            fighter.pos = next_pos;
            fighter.fuel--;
            agent.path_idx++;
        } else {
            agent.status = AgentStatus::ATTACKING;
        }
    }
    
    if (agent.status == AgentStatus::ATTACKING) {
        Point target_pos = red_bases[agent.target_red_base_id].pos;
        int dir = get_dir(fighter.pos, target_pos);
        int attack_count = fighter.missiles;
        
        commands.push_back("attack " + to_string(fighter.id) + " " + to_string(dir) + " " + to_string(attack_count));
        
        fighter.missiles = 0;
        red_bases[agent.target_red_base_id].health -= attack_count;
        red_base_claimed_damage[agent.target_red_base_id] -= attack_count;

        if (red_bases[agent.target_red_base_id].health <= 0) {
            grid[target_pos.r][target_pos.c] = '.';
        }

        agent.status = AgentStatus::MOVING_TO_BASE;
        agent.path = bfs(fighter.pos, blue_bases[agent.return_blue_base_id].pos, false);
        agent.path_idx = 1;
        if (fighter.pos == blue_bases[agent.return_blue_base_id].pos) {
            agent.status = AgentStatus::IDLE;
        }
        return;
    }
    
    if (agent.status == AgentStatus::MOVING_TO_BASE) {
        if (agent.path_idx < agent.path.size()) {
            Point next_pos = agent.path[agent.path_idx];
            int dir = get_dir(fighter.pos, next_pos);
            commands.push_back("move " + to_string(fighter.id) + " " + to_string(dir));
            fighter.pos = next_pos;
            fighter.fuel--;
            agent.path_idx++;
        } else {
            agent.status = AgentStatus::IDLE;
        }
    }
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> m;
    grid.resize(n);
    for (int i = 0; i < n; ++i) cin >> grid[i];

    int num_blue_bases;
    cin >> num_blue_bases;
    blue_bases.resize(num_blue_bases);
    for (int i = 0; i < num_blue_bases; ++i) {
        blue_bases[i].id = i;
        cin >> blue_bases[i].pos.c >> blue_bases[i].pos.r;
        cin >> blue_bases[i].initial_g >> blue_bases[i].initial_c;
        blue_bases[i].g = blue_bases[i].initial_g;
        blue_bases[i].c = blue_bases[i].initial_c;
        long long d, v; 
        cin >> d >> v;
        pos_to_blue_base_id[blue_bases[i].pos] = i;
    }

    int num_red_bases;
    cin >> num_red_bases;
    red_bases.resize(num_red_bases);
    red_base_claimed_damage.resize(num_red_bases, 0);
    for (int i = 0; i < num_red_bases; ++i) {
        red_bases[i].id = i;
        cin >> red_bases[i].pos.c >> red_bases[i].pos.r;
        long long g, c; 
        cin >> g >> c >> red_bases[i].d >> red_bases[i].v;
        red_bases[i].health = red_bases[i].d;
        pos_to_red_base_id[red_bases[i].pos] = i;
    }

    int k;
    cin >> k;
    fighters.resize(k);
    agents.resize(k);
    for (int i = 0; i < k; ++i) {
        fighters[i].id = i;
        cin >> fighters[i].pos.c >> fighters[i].pos.r >> fighters[i].G >> fighters[i].C;
        fighters[i].fuel = 0;
        fighters[i].missiles = 0;
        agents[i].fighter_id = i;
    }

    for (int frame = 0; frame < 15000; ++frame) {
        bool all_valuable_destroyed = true;
        for(const auto& rb : red_bases) {
            if (rb.health > 0 && rb.v > 0) {
                all_valuable_destroyed = false;
                break;
            }
        }
        if (all_valuable_destroyed) break;

        vector<string> commands;
        for (int i = 0; i < k; ++i) {
            step_agent(i, commands);
        }

        for (const auto& cmd : commands) {
            cout << cmd << '\n';
        }
        cout << "OK" << '\n';
    }

    return 0;
}