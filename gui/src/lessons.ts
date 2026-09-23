// The opening lessons. The data is data/lessons.json at the repository root,
// built and checked by python/lessons.py and shared with the Android app.
import data from "../../data/lessons.json";
import type { Color } from "./engine/types";

export interface Text { fa: string; en: string }

export interface LessonMove {
  uci: string;
  san: string;
  fa: string;
  en: string;
}

export interface Lesson {
  id: string;
  group: string;
  side: Color; // the side the lesson teaches
  name: Text;
  summary: Text;
  ideas: { fa: string[]; en: string[] };
  eco: string; // where the line ends, as the engine names it
  tableName: string;
  moves: LessonMove[];
}

export interface LessonGroup { id: string; fa: string; en: string }

export const GROUPS: LessonGroup[] = data.groups;
export const LESSONS: Lesson[] = data.lessons as Lesson[];
